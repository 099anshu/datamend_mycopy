"""Parser for UCR/UEA .ts time series file format."""

import re
from typing import Dict, List, Optional, Tuple
from io import BytesIO
import pandas as pd


class TSParseError(ValueError):
    """Raised when a .ts file cannot be parsed."""


def parse_ts_file(content: bytes) -> Tuple[pd.DataFrame, Dict]:
    """Parse a UCR/UEA .ts file and return DataFrame with metadata.
    
    Args:
        content: Raw bytes of the .ts file
        
    Returns:
        Tuple of (DataFrame containing the time series data, metadata dictionary)
        
    Raises:
        TSParseError: If the file cannot be parsed
    """
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise TSParseError(f"File is not valid UTF-8 text: {exc}") from exc
    
    lines = text.strip().split('\n')
    
    # Parse metadata
    metadata = {}
    data_start_idx = 0
    
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('@'):
            # Parse metadata lines like @problemName Heartbeat
            match = re.match(r'@(\w+)\s+(.+)', line)
            if match:
                key, value = match.groups()
                # Handle special case for classLabel which might have format "true label1 label2 ..."
                if key == 'classLabel':
                    parts = value.split()
                    if parts:
                        metadata[key] = parts[0]  # First part is "true" or "false"
                        if len(parts) > 1:
                            metadata['classNames'] = parts[1:]  # Rest are class names
                else:
                    metadata[key] = value
            elif line == '@data':
                data_start_idx = i + 1
                break
        elif line.startswith('#'):
            # Comment lines, skip
            continue
    
    if data_start_idx == 0:
        raise TSParseError("No @data section found in .ts file")
    
    # Parse data section
    data_lines = lines[data_start_idx:]
    if not data_lines:
        raise TSParseError("No data found after @data section")
    
    # Determine if class labels are expected
    has_class_label = metadata.get('classLabel', '').lower() == 'true'

    # Determine if multivariate (colon-separated dimensions)
    first_line = data_lines[0].strip()
    is_multivariate = ':' in first_line

    records = []
    class_labels = []

    for line in data_lines:
        line = line.strip()
        if not line:
            continue

        if is_multivariate:
            # Multivariate: dimensions separated by colons
            parts = line.split(':')
            if has_class_label:
                last_part = parts[-1]
                if ',' in last_part:
                    # Values and class label mixed
                    values_part = ','.join(parts[:-1])
                    last_values = last_part.rsplit(',', 1)
                    if len(last_values) == 2:
                        values_part += ',' + last_values[0]
                        class_label = last_values[1].strip()
                    else:
                        values_part = ','.join(parts)
                        class_label = None
                else:
                    values_part = ','.join(parts[:-1])
                    class_label = last_part.strip()
            else:
                values_part = ','.join(parts)
                class_label = None

            # Parse values - each value is a time step or dimension
            try:
                values = [float(v.strip()) for v in values_part.split(',') if v.strip()]
            except ValueError as exc:
                raise TSParseError(f"Could not parse numeric values: {exc}") from exc
        else:
            # Univariate: comma-separated values
            parts = line.split(',')
            if has_class_label:
                try:
                    values = [float(v.strip()) for v in parts[:-1] if v.strip()]
                except ValueError as exc:
                    raise TSParseError(f"Could not parse numeric values: {exc}") from exc
                class_label = parts[-1].strip() if parts else None
            else:
                try:
                    values = [float(v.strip()) for v in parts if v.strip()]
                except ValueError as exc:
                    raise TSParseError(f"Could not parse numeric values: {exc}") from exc
                class_label = None

        records.append(values)
        if class_label is not None:
            class_labels.append(class_label)
    
    # Create DataFrame
    if not records:
        raise TSParseError("No valid data records found")
    
    # Check if this is a classification dataset (each row is a separate time series instance)
    # or a time series dataset (each row is a time step)
    is_classification_dataset = metadata.get('classLabel') == 'true'
    
    # Also check if the data format suggests classification (colon-separated with many time steps)
    # Regular time series typically have fewer time steps per row
    num_timesteps_per_row = len(records[0]) if records else 0
    is_likely_classification = is_classification_dataset and num_timesteps_per_row > 10
    
    if is_likely_classification:
        # For classification datasets, we need to transpose the data
        # Each row is an instance, each column is a time step
        # We want each row to be a time step and each column to be a dimension
        
        # Transpose: rows become columns, columns become rows
        num_instances = len(records)
        num_timesteps = len(records[0]) if records else 0
        
        # Create a list where each element is the values for a timestep across all instances
        transposed_data = []
        for t in range(num_timesteps):
            timestep_values = [records[i][t] for i in range(num_instances) if t < len(records[i])]
            transposed_data.append(timestep_values)
        
        # Create column names (one per instance)
        columns = [f'instance_{i}' for i in range(num_instances)]
        
        df = pd.DataFrame(transposed_data, columns=columns)
        
        # Add class labels as a separate column (won't be included in numeric processing)
        if class_labels:
            # We need to expand class labels to match the transposed structure
            # Each timestep row should have all class labels
            expanded_labels = []
            for t in range(num_timesteps):
                expanded_labels.append(class_labels)
            df['class_labels'] = expanded_labels
    else:
        # Regular time series: each row is a time step
        num_dimensions = len(records[0])
        
        # Create column names
        if is_multivariate:
            columns = [f'dim_{i}' for i in range(num_dimensions)]
        else:
            columns = ['value']
        
        df = pd.DataFrame(records, columns=columns)
        
        # Add class label if present
        if class_labels:
            df['class_label'] = class_labels
    
    # Add metadata to DataFrame as attributes
    df.attrs['ts_metadata'] = metadata
    
    return df, metadata


def convert_ts_to_dataframe(df: pd.DataFrame, metadata: Dict) -> pd.DataFrame:
    """Convert parsed .ts data to standard time series DataFrame format.
    
    Args:
        df: DataFrame from parse_ts_file
        metadata: Metadata dictionary from parse_ts_file
        
    Returns:
        DataFrame with timestamp index and signal columns
    """
    # Extract numeric columns only
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    # Create a simple sequential time index (since .ts files don't have timestamps)
    import numpy as np
    num_rows = len(df)
    
    # Create a time index - using hourly intervals starting from a base time
    base_time = pd.Timestamp('2020-01-01', tz='UTC')
    timestamps = pd.date_range(
        start=base_time,
        periods=num_rows,
        freq='h'  # Hourly frequency
    )
    
    result = df[numeric_cols].copy()
    result.index = timestamps
    result.index.name = 'timestamp'
    
    return result