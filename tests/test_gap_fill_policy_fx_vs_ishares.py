import os
import sys
import datetime
from unittest.mock import Mock, patch

import pandas as pd

# Ensure project root is on sys.path so 'src' package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.nightbatch import run_fx_update, ishares_importer


def test_fx_gap_fill_uses_yesterday_as_end_boundary():
    """
    This should pass in current behavior: FX explicitly gap-fills to yesterday.
    """
    with patch("src.nightbatch.run_fx_update.database") as mock_db, \
         patch("src.nightbatch.run_fx_update.my_yf") as mock_yf, \
         patch("src.nightbatch.run_fx_update.fetch_and_fill_price_gaps") as mock_fill:
        mock_db.get_non_eur_asset_currency_start_dates.return_value = {"USD": "2026-06-01"}
        mock_db.get_fx_rate_bounds.return_value = {}
        mock_db.get_fx_rates_for_currency_dates.return_value = []
        mock_db.save_fx_rates_bulk = Mock()

        mock_columns = pd.MultiIndex.from_tuples(
            [
                ("Open", "EURUSD=X"),
                ("High", "EURUSD=X"),
                ("Low", "EURUSD=X"),
                ("Close", "EURUSD=X"),
                ("Volume", "EURUSD=X"),
            ],
            names=["Price", "Ticker"],
        )
        mock_yf.download.return_value = pd.DataFrame(
            [[1.12, 1.13, 1.11, 1.125, 0]],
            index=[pd.Timestamp("2026-06-19")],
            columns=mock_columns,
        )
        mock_fill.return_value = [
            {"date": datetime.date(2026, 6, 20), "value": 1.125, "origin": datetime.date(2026, 6, 19)}
        ]

        with patch("src.nightbatch.run_fx_update.datetime") as mock_datetime:
            mock_datetime.date.today.return_value = datetime.date(2026, 6, 21)
            mock_datetime.timedelta = datetime.timedelta
            mock_datetime.datetime.utcnow.return_value = datetime.datetime(2026, 6, 21, 10, 0, 0)

            run_fx_update.headless_load_missing_fx_rates(dry_run=True)

        # The key policy assertion: FX gap-fill end date should be yesterday (2026-06-20)
        _, start_arg, end_arg, _ = mock_fill.call_args[0]
        assert end_arg == datetime.date(2026, 6, 20)


def test_ishares_gap_fill_should_extend_to_yesterday_on_weekend():
    """
    Intentionally expected to fail before the fix:
    iShares currently gap-fills only up to source max date, not yesterday.
    """
    sheets = {
        "Historisch": pd.DataFrame(
            {
                "per": ["2026-06-19"],
                "Währung": ["USD"],
                "NAV": [100.0],
            }
        ),
        "Ausschüttungen": pd.DataFrame(
            {
                "Fälligkeitsdatum": [],
                "Gesamtausschüttung": [],
            }
        ),
    }

    with patch("src.nightbatch.ishares_importer.pd.read_excel", return_value=sheets), \
         patch("src.nightbatch.ishares_importer.database") as mock_db, \
         patch("src.nightbatch.ishares_importer.date") as mock_date:
        mock_date.today.return_value = datetime.date(2026, 6, 21)
        mock_db.get_asset_prices_for_isin.return_value = []
        mock_db.save_asset_prices_bulk = Mock()

        res = ishares_importer.import_ishares_history_for_ticker(
            isin="IE000TEST01",
            ticker="332655",
            price_currency="USD",
            price_start_date="2026-06-01",
            request_start_date="2026-06-01",
            asset_start_date="2026-06-01",
            dry_run=True,
            excel_bytes=b"FAKE",
        )

    # Desired policy: with run date 2026-06-21, yesterday is 2026-06-20.
    # Starting from 2026-06-19 source NAV, dry-run parsed should include 2026-06-20 via gap-fill.
    assert res["parsed"] == 2
