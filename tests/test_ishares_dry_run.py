import os
import sys
from unittest.mock import Mock, patch

import pandas as pd

# Ensure project root is on sys.path so 'src' package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.nightbatch import ishares_importer


def _sample_sheets_for_dry_run():
    hist = pd.DataFrame(
        {
            "per": ["2023-06-15", "2023-06-16", "2023-06-17"],
            "Währung": ["USD", "USD", "USD"],
            "NAV": [100.0, 101.0, 102.0],
        }
    )
    aussch = pd.DataFrame(
        {
            "Fälligkeitsdatum": ["2023-06-16", "2023-06-17"],
            "Gesamtausschüttung": [0.5, 1.0],
        }
    )
    return {"Historisch": hist, "Ausschüttungen": aussch}


def test_import_ishares_dry_run_skips_db_write_and_returns_compare_stats():
    sheets = _sample_sheets_for_dry_run()

    with patch("src.nightbatch.ishares_importer.pd.read_excel", return_value=sheets), \
         patch("src.nightbatch.ishares_importer.database") as mock_db:
        mock_db.get_asset_prices_for_isin.return_value = [
            {
                "isin": "IE000OHHIBC6",
                "price_date": "2023-06-16",
                "price_close": "101.0",
                "price_date_original": "2023-06-16",
                "dividend_cash": "0.0",
            },
            {
                "isin": "IE000OHHIBC6",
                "price_date": "2023-06-17",
                "price_close": "101.5",
                "price_date_original": "2023-06-17",
                "dividend_cash": "1.0",
            },
        ]
        mock_db.save_asset_prices_bulk = Mock()

        res = ishares_importer.import_ishares_history_for_ticker(
            isin="IE000OHHIBC6",
            ticker="332655",
            price_currency="USD",
            price_start_date="2023-06-16",
            request_start_date="2023-06-16",
            asset_start_date="2023-06-16",
            dry_run=True,
            excel_bytes=b"FAKE-BYTES",
        )

    assert res["parsed"] == 2
    assert res["to_upsert"] == 1
    assert res["unchanged"] == 1
    assert res["changed"] == 1
    assert res["new"] == 0
    assert not mock_db.save_asset_prices_bulk.called


def test_process_all_ishares_assets_dry_run_uses_distinct_min_start_date_and_bounds():
    assets = [
        {
            "isin": "IE000A",
            "ticker": "111",
            "price_currency": "USD",
            "price_start_date": "2023-01-10",
        },
        {
            "isin": "IE000A",
            "ticker": "111",
            "price_currency": "USD",
            "price_start_date": "2023-01-05",
        },
        {
            "isin": "IE000B",
            "ticker": "222",
            "price_currency": "EUR",
            "price_start_date": "2023-02-01",
        },
    ]
    bounds = {
        "IE000A": {"min": pd.to_datetime("2023-01-20").date(), "max": pd.to_datetime("2023-03-01").date()},
        "IE000B": {"min": pd.to_datetime("2023-01-01").date(), "max": pd.to_datetime("2023-03-10").date()},
    }

    captured_calls = []

    def _fake_import(*args, **kwargs):
        captured_calls.append(
            {
                "isin": args[0],
                "ticker": args[1],
                "price_currency": args[2],
                **kwargs,
            }
        )
        return {"parsed": 2, "to_upsert": 1, "unchanged": 1}

    with patch("src.nightbatch.ishares_importer.database") as mock_db, \
         patch("src.nightbatch.ishares_importer.import_ishares_history_for_ticker", side_effect=_fake_import):
        mock_db.get_assets_by_price_source.return_value = assets
        mock_db.get_asset_price_bounds.return_value = bounds

        summary = ishares_importer.process_all_ishares_assets(dry_run=True)

    assert summary["processed"] == 2
    assert summary["parsed"] == 4
    assert summary["to_upsert"] == 2
    assert summary["upserted"] == 0
    assert summary["unchanged"] == 2

    assert len(captured_calls) == 2

    # IE000A should use earliest start date (2023-01-05) and lookback 7 days => 2022-12-29
    call_a = next(c for c in captured_calls if c["isin"] == "IE000A")
    assert call_a["price_start_date"] == "2023-01-05"
    assert call_a["request_start_date"] == "2022-12-29"
    assert call_a["dry_run"] is True

    # IE000B should use incremental refresh from max(2023-03-10)-35 days => 2023-02-03
    call_b = next(c for c in captured_calls if c["isin"] == "IE000B")
    assert call_b["request_start_date"] == "2023-02-03"
    assert call_b["dry_run"] is True
