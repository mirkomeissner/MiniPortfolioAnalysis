import os
import sys
from datetime import date
from unittest.mock import Mock, patch

import pandas as pd

# Ensure project root is on sys.path so 'src' package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.nightbatch import eodhd_price_importer


def test_import_eodhd_dry_run_trims_and_deduplicates_normalized_rows():
    mock_rows = [
        {"date": "2026-06-01", "close": 100.0},
        {"date": "2026-06-02", "close": 101.0},
    ]

    gap_rows = [
        {"date": date(2026, 5, 31), "value": 99.5, "origin": date(2026, 5, 31)},
        {"date": date(2026, 6, 1), "value": 100.0, "origin": date(2026, 6, 1)},
        {"date": date(2026, 6, 2), "value": 101.0, "origin": date(2026, 6, 2)},
    ]

    with patch.dict(os.environ, {"EODHD_API_KEY": "token"}, clear=False), \
         patch("src.nightbatch.eodhd_price_importer._fetch_eodhd_history", return_value=mock_rows), \
         patch("src.nightbatch.eodhd_price_importer.fetch_and_fill_price_gaps", return_value=gap_rows), \
         patch("src.nightbatch.eodhd_price_importer.database") as mock_db, \
         patch("src.nightbatch.eodhd_price_importer.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 3)
        mock_date.side_effect = date
        mock_db.get_asset_prices_for_isin.return_value = [
            {
                "isin": "IE000TEST01",
                "price_date": date(2026, 6, 1),
                "price_close": "100.0",
                "price_date_original": pd.Timestamp("2026-06-01"),
                "dividend_cash": "0",
            }
        ]

        res = eodhd_price_importer.import_eodhd_history_for_ticker(
            isin="IE000TEST01",
            ticker="AAPL.US",
            price_currency="USD",
            price_start_date="2026-06-01",
            request_start_date="2026-05-25",
            asset_start_date="2026-06-01",
            dry_run=True,
        )

    # 2026-05-31 is trimmed (before asset_start), 2026-06-01 unchanged, 2026-06-02 new
    assert res["parsed"] == 2
    assert res["to_upsert"] == 1
    assert res["unchanged"] == 1
    assert res["new"] == 1
    assert res["changed"] == 0


def test_import_eodhd_missing_api_key_returns_error():
    with patch.dict(os.environ, {}, clear=True):
        res = eodhd_price_importer.import_eodhd_history_for_ticker(
            isin="IE000TEST01",
            ticker="AAPL.US",
            price_currency="USD",
            price_start_date="2026-01-01",
            request_start_date="2025-12-25",
            asset_start_date="2026-01-01",
            dry_run=True,
        )

    assert res["error"] == "missing_eodhd_api_key"


def test_process_all_eodhd_assets_uses_distinct_isin_min_start_and_bounds():
    assets = [
        {
            "isin": "IE000A",
            "ticker": "AAPL.US",
            "price_currency": "USD",
            "price_start_date": "2026-01-10",
        },
        {
            "isin": "IE000A",
            "ticker": "AAPL.US",
            "price_currency": "USD",
            "price_start_date": "2026-01-05",
        },
        {
            "isin": "IE000B",
            "ticker": "BMW.XETRA",
            "price_currency": "EUR",
            "price_start_date": "2026-02-01",
        },
    ]
    bounds = {
        "IE000A": {"min": pd.to_datetime("2026-01-20").date(), "max": pd.to_datetime("2026-03-01").date()},
        "IE000B": {"min": pd.to_datetime("2026-01-01").date(), "max": pd.to_datetime("2026-03-10").date()},
    }

    captured_calls = []

    def _fake_import(**kwargs):
        captured_calls.append(kwargs)
        return {"parsed": 2, "to_upsert": 1, "unchanged": 1}

    with patch("src.nightbatch.eodhd_price_importer.database") as mock_db, \
         patch("src.nightbatch.eodhd_price_importer.import_eodhd_history_for_ticker", side_effect=_fake_import):
        mock_db.get_assets_by_price_source.return_value = assets
        mock_db.get_asset_price_bounds.return_value = bounds

        summary = eodhd_price_importer.process_all_eodhd_assets(dry_run=True)

    assert summary["processed"] == 2
    assert summary["parsed"] == 4
    assert summary["to_upsert"] == 2
    assert summary["upserted"] == 0
    assert summary["unchanged"] == 2

    assert len(captured_calls) == 2

    # IE000A earliest start 2026-01-05 and asset_start < min => request_start 2025-12-29
    call_a = next(c for c in captured_calls if c["isin"] == "IE000A")
    assert call_a["price_start_date"] == "2026-01-05"
    assert call_a["request_start_date"] == "2025-12-29"
    assert call_a["dry_run"] is True

    # IE000B incremental: max 2026-03-10 => request_start 2026-02-03
    call_b = next(c for c in captured_calls if c["isin"] == "IE000B")
    assert call_b["request_start_date"] == "2026-02-03"


def test_process_all_eodhd_assets_reports_errors_per_isin():
    with patch("src.nightbatch.eodhd_price_importer.database") as mock_db, \
         patch("src.nightbatch.eodhd_price_importer.import_eodhd_history_for_ticker", return_value={"error": "boom"}):
        mock_db.get_assets_by_price_source.return_value = [
            {
                "isin": "IE000A",
                "ticker": "AAPL.US",
                "price_currency": "USD",
                "price_start_date": "2026-01-01",
            }
        ]
        mock_db.get_asset_price_bounds.return_value = {}

        summary = eodhd_price_importer.process_all_eodhd_assets(dry_run=True)

    assert summary["processed"] == 1
    assert len(summary["errors"]) == 1
    assert summary["errors"][0]["isin"] == "IE000A"
