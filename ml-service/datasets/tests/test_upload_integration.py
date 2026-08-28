"""Integration test for .ts file upload and processing."""

import pytest
import pandas as pd
from datasets.upload_store import save_upload, load_uploaded_dataset, list_uploads
from datasets.ts_analysis import calculate_rolling_statistics, calculate_differences, scale_time_series


def test_heartbeat_upload_and_analysis():
    """Test uploading Heartbeat .ts file and performing analysis."""
    ts_file_path = r"c:\Users\V\Downloads\Datasets for Time Series Analysis\dataset\Heartbeat\Heartbeat_TEST.ts"
    
    try:
        with open(ts_file_path, 'rb') as f:
            content = f.read()
        
        # Upload the file
        dataset_id, profile, uploaded_at = save_upload("Heartbeat_TEST.ts", content)
        
        print(f"✓ Successfully uploaded Heartbeat dataset: {dataset_id}")
        print(f"✓ Profile: {profile.rowCount} rows, {profile.columnCount} columns")
        print(f"✓ Signal columns: {profile.signalColumns[:5]}...")  # Show first 5
        
        # Load the dataset
        df = load_uploaded_dataset(dataset_id)
        
        print(f"✓ Loaded dataset: {len(df)} rows, {len(df.columns)} columns")
        print(f"✓ Index type: {type(df.index)}")
        print(f"✓ First few columns: {df.columns[:5].tolist()}")
        
        # Test rolling statistics
        test_columns = df.columns[:3].tolist()  # Use first 3 columns
        rolling_df = calculate_rolling_statistics(df, window=10, columns=test_columns)
        
        print(f"✓ Rolling statistics calculated")
        print(f"✓ New columns: {[col for col in rolling_df.columns if col not in df.columns][:5]}")
        
        # Test differences
        diff_df = calculate_differences(df, columns=test_columns, periods=1)
        
        print(f"✓ Differences calculated")
        print(f"✓ New columns: {[col for col in diff_df.columns if col not in df.columns][:5]}")
        
        # Test scaling
        scaled_df = scale_time_series(df, columns=test_columns, method='standard')
        
        print(f"✓ Scaling calculated")
        print(f"✓ New columns: {[col for col in scaled_df.columns if col not in df.columns][:5]}")
        
        # List uploads to verify it's stored
        uploads = list_uploads()
        heartbeat_upload = [u for u in uploads if u.datasetId == dataset_id]
        
        assert len(heartbeat_upload) == 1, "Heartbeat upload should be in the list"
        print(f"✓ Dataset found in uploads list")
        
        print("\n✅ All integration tests passed!")
        
    except FileNotFoundError:
        pytest.skip(f"Heartbeat test file not found at {ts_file_path}")
    except Exception as e:
        pytest.fail(f"Integration test failed: {e}")


if __name__ == '__main__':
    print("Running integration test for Heartbeat .ts file upload...")
    print()
    
    try:
        test_heartbeat_upload_and_analysis()
    except Exception as e:
        print(f"Test failed: {e}")
        raise