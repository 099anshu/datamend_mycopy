from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from datasets.live_api_loader import fetch_crypto, fetch_weather, LiveApiError


def _mock_response(json_data, status_ok=True):
    mock = MagicMock()
    mock.json.return_value = json_data
    if status_ok:
        mock.raise_for_status.return_value = None
    else:
        import requests
        mock.raise_for_status.side_effect = requests.HTTPError("boom")
    return mock


@patch("datasets.live_api_loader.requests.get")
def test_fetch_weather_parses_hourly_payload(mock_get):
    mock_get.return_value = _mock_response({
        "hourly": {
            "time": ["2026-08-28T00:00", "2026-08-28T01:00"],
            "temperature_2m": [28.1, 27.9],
            "relative_humidity_2m": [80, 82],
        }
    })
    df = fetch_weather(latitude=19.07, longitude=72.87)
    assert list(df.columns) == ["timestamp", "temperature_2m", "relative_humidity_2m"]
    assert len(df) == 2
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])


@patch("datasets.live_api_loader.requests.get")
def test_fetch_weather_raises_on_missing_hourly(mock_get):
    mock_get.return_value = _mock_response({"unexpected": {}})
    with pytest.raises(LiveApiError):
        fetch_weather()


@patch("datasets.live_api_loader.requests.get")
def test_fetch_crypto_merges_price_marketcap_volume(mock_get):
    mock_get.return_value = _mock_response({
        "prices": [[1700000000000, 35000.0], [1700003600000, 35100.0]],
        "market_caps": [[1700000000000, 6.8e11], [1700003600000, 6.9e11]],
        "total_volumes": [[1700000000000, 2.1e10], [1700003600000, 2.2e10]],
    })
    df = fetch_crypto(coin_id="bitcoin", days=1)
    assert set(df.columns) == {"timestamp", "price", "market_cap", "volume"}
    assert len(df) == 2
    assert df["price"].iloc[0] == 35000.0


@patch("datasets.live_api_loader.requests.get")
def test_fetch_crypto_raises_on_bad_status(mock_get):
    mock_get.return_value = _mock_response({}, status_ok=False)
    with pytest.raises(LiveApiError):
        fetch_crypto()
