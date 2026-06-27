import io
import os
import sys
import pandas as pd
from unittest.mock import patch

# Ensure project root is on sys.path so 'src' package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.nightbatch import ishares_update as ishares_importer


def make_sample_excel_bytes():
    # We will not create a real Excel file (openpyxl may be missing).
    # Instead return DataFrames and let the test monkeypatch pd.read_excel.
    hist = pd.DataFrame({
        'per': ['2023-06-16', '2023-06-17', '2023-06-18'],
        'Währung': ['USD', 'USD', 'USD'],
        'NAV': [100.0, 101.0, 102.0]
    })

    aussch = pd.DataFrame({
        'Fälligkeitsdatum': ['2023-06-17'],
        'Gesamtausschüttung': [0.5]
    })

    return {"Historisch": hist, "Ausschüttungen": aussch}


def test_import_ishares_parsing_dry_run():
    sheets = make_sample_excel_bytes()

    with patch("src.nightbatch.ishares_update.pd.read_excel", return_value=sheets), \
         patch("src.utils.data_import_helpers.database") as mock_helper_db, \
         patch("src.utils.data_import_helpers.calculate_gap_fill_end_date", return_value=pd.to_datetime("2023-06-18").date()):
        mock_helper_db.get_asset_prices_for_isin.return_value = []

        res = ishares_importer.import_ishares_history_for_ticker(
            isin='IE000OHHIBC6',
            ticker='332655',
            price_currency='USD',
            price_start_date='2023-06-01',
            dry_run=True,
            excel_bytes=b"FAKE-BYTES-WHICH-IS-IGNORED"
        )

    assert isinstance(res, dict)
    assert res.get('parsed') == 3
    assert res.get('number_fetched') == 3
    assert res.get('number_trimmed') == 3
    assert res.get('to_upsert') == 3


def test_import_ishares_currency_mismatch_returns_skipped_result():
    sheets = {
        "Historisch": pd.DataFrame(
            {
                "per": ["2023-06-16"],
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

    with patch("src.nightbatch.ishares_update.pd.read_excel", return_value=sheets):
        res = ishares_importer.import_ishares_history_for_ticker(
            isin="IE000OHHIBC6",
            ticker="332655",
            price_currency="EUR",
            price_start_date="2023-06-01",
            dry_run=True,
            excel_bytes=b"FAKE-BYTES-WHICH-IS-IGNORED",
        )

    assert res == {"skipped": True, "reason": "currency_mismatch"}
