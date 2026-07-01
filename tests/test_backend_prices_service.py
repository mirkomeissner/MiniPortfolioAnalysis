import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.services.prices_service import build_asset_prices_df, build_fx_rates_df


def test_build_asset_prices_df_returns_expected_columns_for_empty_input():
    df = build_asset_prices_df([])

    assert list(df.columns) == [
        "ISIN",
        "Name",
        "Price Date",
        "Price Close",
        "Price Currency",
        "Dividend Cash",
        "Split Factor",
    ]
    assert df.empty


def test_build_asset_prices_df_flattens_asset_metadata():
    df = build_asset_prices_df(
        [
            {
                "isin": "TEST123",
                "price_date": "2026-06-30",
                "price_close": 101.5,
                "dividend_cash": 0.5,
                "split_factor": 1.0,
                "asset_static_data": {
                    "name": "Test Asset",
                    "price_currency": "USD",
                },
            }
        ]
    )

    assert list(df.columns) == [
        "ISIN",
        "Name",
        "Price Date",
        "Price Close",
        "Price Currency",
        "Dividend Cash",
        "Split Factor",
    ]
    assert df.to_dict("records") == [
        {
            "ISIN": "TEST123",
            "Name": "Test Asset",
            "Price Date": "2026-06-30",
            "Price Close": 101.5,
            "Price Currency": "USD",
            "Dividend Cash": 0.5,
            "Split Factor": 1.0,
        }
    ]


def test_build_fx_rates_df_returns_expected_columns_for_empty_input():
    df = build_fx_rates_df([])

    assert list(df.columns) == [
        "Currency",
        "Date",
        "Exchange Rate",
        "Date Original",
        "Created At",
        "Updated At",
    ]
    assert df.empty


def test_build_fx_rates_df_renames_columns():
    df = build_fx_rates_df(
        [
            {
                "currency": "USD",
                "rate_date": "2026-06-30",
                "exchange_rate": 1.1723,
                "rate_date_original": "2026-06-30",
                "created_at": "2026-07-01T00:00:00",
                "updated_at": "2026-07-01T00:00:00",
            }
        ]
    )

    assert list(df.columns) == [
        "Currency",
        "Date",
        "Exchange Rate",
        "Date Original",
        "Created At",
        "Updated At",
    ]
    assert df.iloc[0].to_dict() == {
        "Currency": "USD",
        "Date": "2026-06-30",
        "Exchange Rate": 1.1723,
        "Date Original": "2026-06-30",
        "Created At": "2026-07-01T00:00:00",
        "Updated At": "2026-07-01T00:00:00",
    }