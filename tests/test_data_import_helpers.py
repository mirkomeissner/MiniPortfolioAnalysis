import os
import sys
from datetime import date, datetime

# Ensure project root is on sys.path so 'src' package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.utils.data_import_helpers import (
    normalize_float,
    normalize_date,
    normalize_value,
    calculate_request_start_date,
    compare_and_deduplicate,
)


def test_normalize_float_handles_locale_and_rounding():
    assert normalize_float("1.234,56", decimals=2) == 1234.56
    assert normalize_float("1,234.56", decimals=2) == 1234.56
    assert normalize_float("", decimals=2) is None
    assert normalize_float(None, decimals=2) is None


def test_normalize_date_handles_iso_and_eu():
    assert normalize_date("2025-06-10") == "2025-06-10"
    assert normalize_date("10.06.2025") == "2025-06-10"
    assert normalize_date(date(2025, 6, 10)) == "2025-06-10"
    assert normalize_date(datetime(2025, 6, 10, 12, 0, 0)) == "2025-06-10"


def test_normalize_value_dispatch():
    assert normalize_value("  foo ", "str") == "foo"
    assert normalize_value("1,5", "float", decimals=2) == 1.5
    assert normalize_value("2025-06-10", "date") == "2025-06-10"


def test_calculate_request_start_date_rules():
    asset_start = date(2025, 1, 10)

    no_bounds = calculate_request_start_date(asset_start, None, lookback_days=7, refresh_days=35)
    assert no_bounds == date(2025, 1, 3)

    missing_max = calculate_request_start_date(asset_start, {"min": date(2025, 1, 1), "max": None}, 7, 35)
    assert missing_max == date(2025, 1, 3)

    older_than_min = calculate_request_start_date(asset_start, {"min": date(2025, 2, 1), "max": date(2025, 6, 1)}, 7, 35)
    assert older_than_min == date(2025, 1, 3)

    incremental = calculate_request_start_date(asset_start, {"min": date(2024, 1, 1), "max": date(2025, 6, 1)}, 7, 35)
    assert incremental == date(2025, 4, 27)


def test_compare_and_deduplicate_normalized_mixed_types():
    loaded = [
        {
            "isin": "IE0001",
            "price_date": "2025-06-10",
            "price_close": 100.0,
            "price_date_original": "2025-06-10",
            "dividend_cash": 0.0,
        },
        {
            "isin": "IE0001",
            "price_date": "2025-06-11",
            "price_close": 101.0,
            "price_date_original": "2025-06-11",
            "dividend_cash": 1.0,
        },
    ]
    existing = [
        {
            "isin": "IE0001",
            "price_date": date(2025, 6, 10),
            "price_close": "100.0000",
            "price_date_original": datetime(2025, 6, 10, 0, 0, 0),
            "dividend_cash": "0",
        },
        {
            "isin": "IE0001",
            "price_date": date(2025, 6, 11),
            "price_close": "100.5000",
            "price_date_original": datetime(2025, 6, 11, 0, 0, 0),
            "dividend_cash": "1.0",
        },
    ]

    upsert, summary = compare_and_deduplicate(
        loaded_records=loaded,
        existing_records=existing,
        key_fields=["isin", "price_date"],
        compare_fields=["price_close", "price_date_original", "dividend_cash"],
        normalizers={
            "price_date": normalize_date,
            "price_date_original": normalize_date,
            "price_close": lambda v: normalize_float(v, decimals=10),
            "dividend_cash": lambda v: normalize_float(v, decimals=10),
        },
    )

    assert summary["loaded"] == 2
    assert summary["unchanged"] == 1
    assert summary["changed"] == 1
    assert summary["new"] == 0
    assert summary["to_upsert"] == 1
    assert len(upsert) == 1
    assert upsert[0]["price_date"] == "2025-06-11"
