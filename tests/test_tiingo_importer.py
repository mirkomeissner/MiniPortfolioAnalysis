import os
import sys
from datetime import date
from unittest.mock import patch

import pandas as pd

# Ensure project root is on sys.path so 'src' package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.nightbatch import tiingo_price_importer


def test_import_tiingo_dry_run_uses_dividend_and_split_fields_and_deduplicates():
    mock_rows = [
        {"date": "2026-06-01T00:00:00.000Z", "close": 100.0, "divCash": 0.0, "splitFactor": 1.0},
        {"date": "2026-06-02T00:00:00.000Z", "close": 101.0, "divCash": 0.5, "splitFactor": 1.0},
        {"date": "2026-06-03T00:00:00.000Z", "close": 50.5, "divCash": 0.0, "splitFactor": 2.0},
    ]

    gap_rows = [
        {"date": date(2026, 5, 31), "value": 99.0, "origin": date(2026, 5, 31)},
        {"date": date(2026, 6, 1), "value": 100.0, "origin": date(2026, 6, 1)},
        {"date": date(2026, 6, 2), "value": 101.0, "origin": date(2026, 6, 2)},
        {"date": date(2026, 6, 3), "value": 50.5, "origin": date(2026, 6, 3)},
    ]

    with patch.dict(os.environ, {"TIINGO_API_KEY": "token"}, clear=False), \
         patch("src.nightbatch.tiingo_price_importer._fetch_tiingo_history", return_value=mock_rows), \
         patch("src.nightbatch.tiingo_price_importer.fetch_and_fill_price_gaps", return_value=gap_rows), \
         patch("src.nightbatch.tiingo_price_importer.database") as mock_db, \
         patch("src.nightbatch.tiingo_price_importer.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 4)
        mock_date.side_effect = date
        mock_db.get_asset_prices_for_isin.return_value = [
            {
                "isin": "IE000TEST01",
                "price_date": date(2026, 6, 1),
                "price_close": "100.0",
                "price_date_original": pd.Timestamp("2026-06-01"),
                "dividend_cash": "0",
                "split_factor": "1",
            }
        ]

        res = tiingo_price_importer.import_tiingo_history_for_ticker(
            isin="IE000TEST01",
            ticker="aapl",
            price_currency="USD",
            price_start_date="2026-06-01",
            request_start_date="2026-05-25",
            asset_start_date="2026-06-01",
            dry_run=True,
        )

    # 2026-05-31 trimmed; 2026-06-01 unchanged; 2026-06-02 and 2026-06-03 new
    assert res["parsed"] == 3
    assert res["to_upsert"] == 2
    assert res["unchanged"] == 1
    assert res["new"] == 2
    assert res["changed"] == 0


def test_import_tiingo_missing_api_key_returns_error():
    with patch.dict(os.environ, {}, clear=True):
        res = tiingo_price_importer.import_tiingo_history_for_ticker(
            isin="IE000TEST01",
            ticker="aapl",
            price_currency="USD",
            price_start_date="2026-01-01",
            request_start_date="2025-12-25",
            asset_start_date="2026-01-01",
            dry_run=True,
        )

    assert res["error"] == "missing_tiingo_api_key"


def test_process_all_tiingo_assets_uses_distinct_isin_min_start_and_bounds():
    assets = [
        {
            "isin": "IE000A",
            "ticker": "aapl",
            "price_currency": "USD",
            "price_start_date": "2026-01-10",
        },
        {
            "isin": "IE000A",
            "ticker": "aapl",
            "price_currency": "USD",
            "price_start_date": "2026-01-05",
        },
        {
            "isin": "IE000B",
            "ticker": "msft",
            "price_currency": "USD",
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

    with patch("src.nightbatch.tiingo_price_importer.database") as mock_db, \
         patch("src.nightbatch.tiingo_price_importer.import_tiingo_history_for_ticker", side_effect=_fake_import):
        mock_db.get_assets_by_price_source.return_value = assets
        mock_db.get_asset_price_bounds.return_value = bounds

        summary = tiingo_price_importer.process_all_tiingo_assets(dry_run=True)

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


def test_process_all_tiingo_assets_reports_errors_per_isin():
    with patch("src.nightbatch.tiingo_price_importer.database") as mock_db, \
         patch("src.nightbatch.tiingo_price_importer.import_tiingo_history_for_ticker", return_value={"error": "boom"}):
        mock_db.get_assets_by_price_source.return_value = [
            {
                "isin": "IE000A",
                "ticker": "aapl",
                "price_currency": "USD",
                "price_start_date": "2026-01-01",
            }
        ]
        mock_db.get_asset_price_bounds.return_value = {}

        summary = tiingo_price_importer.process_all_tiingo_assets(dry_run=True)

    assert summary["processed"] == 1
    assert len(summary["errors"]) == 1
    assert summary["errors"][0]["isin"] == "IE000A"
