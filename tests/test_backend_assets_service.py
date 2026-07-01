import os
import sys
from unittest.mock import Mock


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.services.assets_service import build_assets_df
from backend.app.services.assets_service import create_asset, search_exchange_ticker_records, update_asset


def test_build_assets_df_returns_expected_columns_for_empty_input():
    df = build_assets_df([])

    assert list(df.columns) == [
        "ISIN",
        "Name",
        "Ticker",
        "Risk Currency",
        "Type",
        "Asset Class",
        "Region",
        "Sector",
        "Industry",
        "Country",
        "Price Source",
        "Price Currency",
        "Price Start Date",
        "Closed On",
        "Created At",
        "Created By",
        "Updated At",
        "Updated By",
    ]
    assert df.empty


def test_build_assets_df_preserves_expected_order_for_payload():
    df = build_assets_df(
        [
            {
                "ISIN": "AAA",
                "Name": "Alpha",
                "Ticker": "ALP",
                "Risk Currency": "USD",
                "Type": "ETF",
                "Asset Class": "Equity",
                "Region": "North America",
                "Sector": "Technology",
                "Industry": "Software",
                "Country": "US",
                "Price Source": "Yahoo",
                "Price Currency": "USD",
                "Price Start Date": "2026-01-01",
                "Closed On": None,
                "Created At": "2026-01-01T00:00:00",
                "Created By": "admin",
                "Updated At": "2026-06-01T00:00:00",
                "Updated By": "admin2",
            }
        ]
    )

    assert df.iloc[0].to_dict()["ISIN"] == "AAA"
    assert list(df.columns)[0:4] == ["ISIN", "Name", "Ticker", "Risk Currency"]


def test_build_assets_df_normalizes_missing_closed_on_to_none():
    df = build_assets_df(
        [
            {
                "ISIN": "AAA",
                "Name": "Alpha",
                "Closed On": None,
            }
        ]
    )

    assert df.to_dict("records") == [{"ISIN": "AAA", "Name": "Alpha", "Closed On": None}]


def test_create_asset_calls_repository_save_and_returns_payload():
    repository = Mock()
    payload = {"isin": "AAA", "name": "Alpha"}

    result = create_asset(payload, repository=repository)

    repository.save_asset_static_data.assert_called_once_with(payload)
    assert result == payload


def test_update_asset_calls_repository_update_and_returns_payload():
    repository = Mock()
    payload = {"name": "Alpha Updated", "closed_on": None}

    result = update_asset("AAA", payload, repository=repository)

    repository.update_asset_static_data.assert_called_once_with("AAA", payload)
    assert result == {"isin": "AAA", **payload}


def test_search_exchange_ticker_records_calls_repository():
    repository = Mock()
    repository.search_exchange_tickers.return_value = [{"ticker_code": "ALP", "isin": "AAA"}]

    result = search_exchange_ticker_records(isin="AAA", name="Alpha", active_only=False, repository=repository)

    repository.search_exchange_tickers.assert_called_once_with(isin="AAA", name="Alpha", active_only=False)
    assert result == [{"ticker_code": "ALP", "isin": "AAA"}]