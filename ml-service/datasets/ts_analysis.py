"""Time series analysis utilities using sktime and pytimetk libraries."""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Tuple


def calculate_rolling_statistics(
    df: pd.DataFrame,
    window: int = 24,
    columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """Calculate rolling statistics for time series data.
    
    Args:
        df: DataFrame with time series data
        window: Rolling window size
        columns: Specific columns to process (None for all)
        
    Returns:
        DataFrame with additional rolling statistics columns
    """
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    result = df.copy()
    
    for col in columns:
        if col in df.columns:
            # Rolling mean
            result[f'{col}_rolling_mean'] = df[col].rolling(window=window, min_periods=1).mean()
            # Rolling std
            result[f'{col}_rolling_std'] = df[col].rolling(window=window, min_periods=1).std()
            # Rolling min/max
            result[f'{col}_rolling_min'] = df[col].rolling(window=window, min_periods=1).min()
            result[f'{col}_rolling_max'] = df[col].rolling(window=window, min_periods=1).max()
    
    return result


def calculate_differences(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    periods: int = 1
) -> pd.DataFrame:
    """Calculate differences for time series data.
    
    Args:
        df: DataFrame with time series data
        columns: Specific columns to process (None for all)
        periods: Number of periods to shift for difference calculation
        
    Returns:
        DataFrame with additional difference columns
    """
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    result = df.copy()
    
    for col in columns:
        if col in df.columns:
            result[f'{col}_diff'] = df[col].diff(periods=periods)
            # Percentage change
            result[f'{col}_pct_change'] = df[col].pct_change(periods=periods)
    
    return result


def scale_time_series(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    method: str = 'standard'
) -> pd.DataFrame:
    """Scale time series data using various methods.
    
    Args:
        df: DataFrame with time series data
        columns: Specific columns to process (None for all)
        method: Scaling method ('standard', 'minmax', 'robust')
        
    Returns:
        DataFrame with scaled columns
    """
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    result = df.copy()
    
    for col in columns:
        if col in df.columns:
            if method == 'standard':
                # Z-score normalization
                mean = df[col].mean()
                std = df[col].std()
                if std != 0:
                    result[f'{col}_scaled'] = (df[col] - mean) / std
                else:
                    result[f'{col}_scaled'] = 0
            elif method == 'minmax':
                # Min-max scaling
                min_val = df[col].min()
                max_val = df[col].max()
                if max_val != min_val:
                    result[f'{col}_scaled'] = (df[col] - min_val) / (max_val - min_val)
                else:
                    result[f'{col}_scaled'] = 0.5
            elif method == 'robust':
                # Robust scaling using median and IQR
                median = df[col].median()
                q75 = df[col].quantile(0.75)
                q25 = df[col].quantile(0.25)
                iqr = q75 - q25
                if iqr != 0:
                    result[f'{col}_scaled'] = (df[col] - median) / iqr
                else:
                    result[f'{col}_scaled'] = 0
    
    return result


def detect_trend(
    series: pd.Series,
    method: str = 'linear'
) -> Dict[str, float]:
    """Detect trend in time series using various methods.
    
    Args:
        series: Time series data
        method: Trend detection method ('linear', 'lowess')
        
    Returns:
        Dictionary with trend information
    """
    result = {
        'method': method,
        'slope': 0.0,
        'intercept': 0.0,
        'r_squared': 0.0
    }
    
    if len(series) < 2:
        return result
    
    x = np.arange(len(series))
    y = series.values
    
    if method == 'linear':
        # Linear regression
        try:
            from scipy import stats
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            result['slope'] = float(slope)
            result['intercept'] = float(intercept)
            result['r_squared'] = float(r_value ** 2)
            result['p_value'] = float(p_value)
        except Exception:
            # Fallback to simple calculation if scipy not available
            try:
                slope = (y[-1] - y[0]) / (len(y) - 1) if len(y) > 1 else 0
                intercept = y[0]
                result['slope'] = float(slope)
                result['intercept'] = float(intercept)
            except Exception:
                pass
    
    return result


def calculate_seasonality(
    series: pd.Series,
    period: Optional[int] = None
) -> Dict[str, float]:
    """Calculate seasonality metrics for time series.
    
    Args:
        series: Time series data
        period: Seasonality period (None for auto-detection)
        
    Returns:
        Dictionary with seasonality information
    """
    result = {
        'period': period,
        'strength': 0.0,
        'seasonal_component': None
    }
    
    if len(series) < 4:
        return result
    
    try:
        from scipy import signal
        # Auto-detect period using FFT
        if period is None:
            # Simple period detection using autocorrelation
            autocorr = np.correlate(series - series.mean(), series - series.mean(), mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            # Find first significant peak after lag 0
            peaks, _ = signal.find_peaks(autocorr[1:], height=0.1 * autocorr[0])
            if len(peaks) > 0:
                period = peaks[0] + 1
        
        if period and period > 0 and period < len(series) // 2:
            result['period'] = period
            # Calculate seasonal strength (simplified)
            seasonal_pattern = []
            for i in range(period):
                # Extract values at this seasonal position
                seasonal_values = series.iloc[i::period].values
                if len(seasonal_values) > 1:
                    seasonal_pattern.append(np.mean(seasonal_values))
            
            if seasonal_pattern:
                seasonal_pattern = np.array(seasonal_pattern)
                # Normalize
                seasonal_pattern = (seasonal_pattern - seasonal_pattern.mean()) / (seasonal_pattern.std() + 1e-8)
                result['seasonal_component'] = seasonal_pattern.tolist()
                # Calculate strength as variance of seasonal pattern
                result['strength'] = float(np.var(seasonal_pattern))
    
    except Exception:
        pass
    
    return result


def decompose_time_series(
    series: pd.Series,
    period: Optional[int] = None,
    model: str = 'additive'
) -> Dict[str, np.ndarray]:
    """Decompose time series into trend, seasonal, and residual components.
    
    Args:
        series: Time series data
        period: Seasonality period
        model: Decomposition model ('additive' or 'multiplicative')
        
    Returns:
        Dictionary with decomposition components
    """
    result = {
        'trend': np.zeros(len(series)),
        'seasonal': np.zeros(len(series)),
        'residual': np.zeros(len(series)),
        'period': period
    }
    
    if len(series) < 4:
        return result
    
    try:
        from statsmodels.tsa.seasonal import seasonal_decompose
        
        # Ensure we have enough data for decomposition
        if period is None:
            # Default to reasonable period based on data length
            period = min(len(series) // 2, 12) if len(series) >= 12 else None
        
        if period and period >= 2:
            decomposition = seasonal_decompose(
                series,
                model=model,
                period=period,
                extrapolate_trend='freq'
            )
            
            result['trend'] = decomposition.trend.values
            result['seasonal'] = decomposition.seasonal.values
            result['residual'] = decomposition.resid.values
            result['period'] = period
    except Exception:
        # Fallback to simple decomposition if statsmodels not available
        # Simple moving average as trend
        window = min(period if period else 12, len(series) // 4)
        if window >= 2:
            result['trend'] = series.rolling(window=window, center=True, min_periods=1).mean().values
            result['residual'] = (series - result['trend']).values
    
    return result


def calculate_statistics_summary(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None
) -> Dict[str, Dict[str, float]]:
    """Calculate comprehensive statistics summary for time series.
    
    Args:
        df: DataFrame with time series data
        columns: Specific columns to process (None for all numeric)
        
    Returns:
        Dictionary with statistics for each column
    """
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    summary = {}
    
    for col in columns:
        if col in df.columns:
            series = df[col].dropna()
            if len(series) > 0:
                summary[col] = {
                    'count': len(series),
                    'mean': float(series.mean()),
                    'std': float(series.std()),
                    'min': float(series.min()),
                    'max': float(series.max()),
                    'median': float(series.median()),
                    'q25': float(series.quantile(0.25)),
                    'q75': float(series.quantile(0.75)),
                    'skewness': float(series.skew()) if len(series) > 3 else 0.0,
                    'kurtosis': float(series.kurtosis()) if len(series) > 4 else 0.0,
                }
    
    return summary


def create_interactive_data_structure(
    df: pd.DataFrame,
    columns: List[str],
    scores: Optional[np.ndarray] = None,
    threshold: Optional[float] = None
) -> List[Dict]:
    """Create data structure suitable for interactive visualization.
    
    Args:
        df: DataFrame with time series data
        columns: Columns to include
        scores: Anomaly scores (optional)
        threshold: Anomaly threshold (optional)
        
    Returns:
        List of dictionaries with time series data points
    """
    result = []
    
    for idx, timestamp in enumerate(df.index):
        point = {
            'timestamp': timestamp.isoformat(),
            'formattedTime': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'values': {}
        }
        
        for col in columns:
            if col in df.columns:
                point['values'][col] = float(df.iloc[idx][col]) if pd.notna(df.iloc[idx][col]) else None
        
        if scores is not None and idx < len(scores):
            point['score'] = float(scores[idx])
            if threshold is not None:
                point['isAnomaly'] = scores[idx] >= threshold
                point['severity'] = 'HIGH' if scores[idx] > 0.9 else ('MEDIUM' if scores[idx] > 0.6 else 'LOW')
        
        result.append(point)
    
    return result