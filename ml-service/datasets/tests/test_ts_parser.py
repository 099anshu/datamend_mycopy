"""Tests for .ts file parser."""

import pytest
import pandas as pd
import numpy as np
from datasets.ts_parser import parse_ts_file, convert_ts_to_dataframe, TSParseError


def test_parse_heartbeat_ts_file():
    """Test parsing the Heartbeat .ts file."""
    # Read the actual Heartbeat file
    ts_file_path = r"c:\Users\V\Downloads\Datasets for Time Series Analysis\dataset\Heartbeat\Heartbeat_TEST.ts"
    
    try:
        with open(ts_file_path, 'rb') as f:
            content = f.read()
        
        df, metadata = parse_ts_file(content)
        
        # Verify metadata was parsed
        assert metadata is not None
        assert 'problemName' in metadata
        assert metadata['problemName'] == 'Heartbeat'
        assert metadata['classLabel'] == 'true'
        assert 'classNames' in metadata
        assert 'normal' in metadata['classNames']
        assert 'abnormal' in metadata['classNames']
        
        # Verify DataFrame structure
        assert df is not None
        assert len(df) > 0
        
        # Heartbeat is a classification dataset with 405 timesteps and multiple instances
        # After transposition, we should have 405 rows (timesteps) and N columns (instances)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        print(f"✓ Successfully parsed Heartbeat dataset: {len(df)} timesteps, {len(numeric_cols)} instances")
        print(f"✓ Metadata: {metadata}")
        
        # Check that class labels were parsed (stored differently for classification datasets)
        if 'class_labels' in df.columns:
            # Classification dataset - each row has a list of class labels
            first_row_labels = df['class_labels'].iloc[0]
            print(f"✓ Class labels found: {len(first_row_labels)} unique labels in first timestep")
            assert len(first_row_labels) > 0
        
        # Test conversion to standard time series format
        ts_df = convert_ts_to_dataframe(df, metadata)
        
        # Verify the converted DataFrame
        assert isinstance(ts_df.index, pd.DatetimeIndex)
        assert len(ts_df) == len(df)
        assert ts_df.index.name == 'timestamp'
        
        print(f"✓ Successfully converted to time series format with {len(ts_df)} timestamps")
        
    except FileNotFoundError:
        pytest.skip(f"Heartbeat test file not found at {ts_file_path}")
    except Exception as e:
        pytest.fail(f"Failed to parse Heartbeat file: {e}")


def test_parse_simple_ts_file():
    """Test parsing a simple synthetic .ts file (classification format)."""
    # Create a simple .ts file content - this is a classification dataset
    # Each row is an instance, values are time steps, colon separates class label
    # Use more timesteps to trigger classification logic (>10 threshold)
    instance1_values = ",".join([f"{i+1}.0" for i in range(15)])
    instance2_values = ",".join([f"{i+2}.0" for i in range(15)])
    
    ts_content = f"""@problemName TestDataset
@timeStamps false
@missing false
@univariate false
@dimensions 2
@equalLength true
@seriesLength 15
@classLabel true A B
@data
{instance1_values}:A
{instance2_values}:B
""".encode('utf-8')
    
    df, metadata = parse_ts_file(ts_content)
    
    # Verify metadata
    assert metadata['problemName'] == 'TestDataset'
    assert metadata['dimensions'] == '2'
    assert metadata['univariate'] == 'false'
    assert metadata['classLabel'] == 'true'
    
    # For classification datasets, the parser transposes the data
    # Each row becomes a timestep, each column becomes an instance
    assert len(df) == 15  # 15 timesteps
    assert 'instance_0' in df.columns
    assert 'instance_1' in df.columns
    assert 'class_labels' in df.columns
    
    # Verify values (transposed)
    assert df['instance_0'].tolist() == [i+1.0 for i in range(15)]
    assert df['instance_1'].tolist() == [i+2.0 for i in range(15)]
    
    print("✓ Successfully parsed simple test .ts file (classification format)")


def test_parse_univariate_ts_file():
    """Test parsing a univariate .ts file (classification format)."""
    instance1_values = ",".join([f"{i+1}.0" for i in range(15)])
    instance2_values = ",".join([f"{i+2}.0" for i in range(15)])
    
    ts_content = f"""@problemName UnivariateTest
@univariate true
@dimensions 1
@seriesLength 15
@classLabel true normal abnormal
@data
{instance1_values}:normal
{instance2_values}:abnormal
""".encode('utf-8')
    
    df, metadata = parse_ts_file(ts_content)
    
    # Verify metadata
    assert metadata['univariate'] == 'true'
    assert metadata['dimensions'] == '1'
    assert metadata['classLabel'] == 'true'
    
    # For classification datasets, the parser transposes the data
    assert len(df) == 15  # 15 timesteps
    assert 'instance_0' in df.columns
    assert 'instance_1' in df.columns
    assert 'class_labels' in df.columns
    
    # Verify values (transposed)
    assert df['instance_0'].tolist() == [i+1.0 for i in range(15)]
    assert df['instance_1'].tolist() == [i+2.0 for i in range(15)]
    
    print("✓ Successfully parsed univariate test .ts file (classification format)")


def test_convert_to_dataframe():
    """Test conversion to standard time series DataFrame."""
    # Create a simple DataFrame
    df = pd.DataFrame({
        'dim_0': [1.0, 2.0, 3.0],
        'dim_1': [4.0, 5.0, 6.0],
        'class_label': ['A', 'B', 'A']
    })
    
    metadata = {'problemName': 'Test', 'dimensions': '2'}
    
    ts_df = convert_ts_to_dataframe(df, metadata)
    
    # Verify conversion
    assert isinstance(ts_df.index, pd.DatetimeIndex)
    assert len(ts_df) == 3
    assert 'dim_0' in ts_df.columns
    assert 'dim_1' in ts_df.columns
    assert 'class_label' not in ts_df.columns  # Non-numeric columns should be excluded
    
    print("✓ Successfully converted DataFrame to time series format")


def test_parse_regular_timeseries():
    """Test parsing a regular time series (non-classification format)."""
    # This is a regular time series where each row is a timestep
    # Use classLabel false to ensure it's treated as regular time series
    # Use colon separator for multivariate data
    ts_content = b"""@problemName RegularTimeSeries
@timeStamps true
@missing false
@univariate false
@dimensions 2
@equalLength true
@seriesLength 3
@classLabel false
@data
1.0:2.0
3.0:4.0
5.0:6.0
"""
    
    df, metadata = parse_ts_file(ts_content)
    
    # Verify metadata
    assert metadata['problemName'] == 'RegularTimeSeries'
    assert metadata['classLabel'] == 'false'
    
    # For regular time series, each row is a timestep
    assert len(df) == 3  # 3 timesteps
    assert 'dim_0' in df.columns
    assert 'dim_1' in df.columns
    assert 'class_labels' not in df.columns  # No class labels for non-classification
    
    # Verify values
    assert df['dim_0'].tolist() == [1.0, 3.0, 5.0]
    assert df['dim_1'].tolist() == [2.0, 4.0, 6.0]
    
    print("✓ Successfully parsed regular time series format")


if __name__ == '__main__':
    # Run tests manually for quick verification
    print("Running .ts parser tests...")
    print()
    
    try:
        test_parse_simple_ts_file()
        test_parse_univariate_ts_file()
        test_convert_to_dataframe()
        test_parse_heartbeat_ts_file()
        
        print()
        print("All tests passed! ✓")
    except Exception as e:
        print(f"Test failed: {e}")
        raise