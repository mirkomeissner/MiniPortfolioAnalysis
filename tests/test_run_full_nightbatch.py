import os
import sys
from unittest.mock import patch

# Ensure project root is on sys.path so 'src' package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import src.nightbatch.fx_update as fx_update
import src.nightbatch.eodhd_update as eodhd_update
import src.nightbatch.tiingo_update as tiingo_update
import src.nightbatch.ishares_update as ishares_update


def _run_all_steps(dry_run: bool) -> dict:
    """
    Runs all 4 nightbatch update scripts in sequence, mirroring the full
    nightbatch workflow: FX rates → EODHD prices → TIINGO prices → iShares prices.
    """
    fx_summary = fx_update.headless_load_missing_fx_rates(dry_run=dry_run)
    eodhd_summary = eodhd_update.process_all_eodhd_assets(dry_run=dry_run)
    tiingo_summary = tiingo_update.process_all_tiingo_assets(dry_run=dry_run)
    ishares_summary = ishares_update.process_all_ishares_assets(dry_run=dry_run)
    return {
        "fx": fx_summary,
        "eodhd": eodhd_summary,
        "tiingo": tiingo_summary,
        "ishares": ishares_summary,
        "dry_run": dry_run,
    }


def test_full_nightbatch_sequence_dry_run_no_assets():
    """
    Runs all 4 update scripts in sequence (dry_run=True) with DB returning no
    assets or currencies, verifying every step executes without error.
    """
    with patch("src.nightbatch.fx_update.database") as mock_fx_db, \
         patch("src.nightbatch.fx_update.my_yf"), \
         patch("src.utils.data_import_helpers.database") as mock_helpers_db:

        mock_fx_db.get_non_eur_asset_currency_start_dates.return_value = {}
        mock_fx_db.get_fx_rate_bounds.return_value = {}
        mock_helpers_db.get_assets_by_price_source.return_value = []
        mock_helpers_db.get_asset_price_bounds.return_value = {}

        result = _run_all_steps(dry_run=True)

    # FX returns None when no currencies exist; batch scripts return empty summary dicts
    assert result["dry_run"] is True
    assert isinstance(result["eodhd"], dict)
    assert isinstance(result["tiingo"], dict)
    assert isinstance(result["ishares"], dict)


def test_full_nightbatch_sequence_forwards_dry_run_true():
    """
    Verifies that dry_run=True is forwarded to all 4 individual update scripts
    when they are called in sequence.
    """
    with patch("src.nightbatch.fx_update.headless_load_missing_fx_rates") as mock_fx, \
         patch("src.nightbatch.eodhd_update.process_all_eodhd_assets") as mock_eodhd, \
         patch("src.nightbatch.tiingo_update.process_all_tiingo_assets") as mock_tiingo, \
         patch("src.nightbatch.ishares_update.process_all_ishares_assets") as mock_ish:

        mock_fx.return_value = {"loaded": 10, "to_upsert": 3, "dry_run": True}
        mock_eodhd.return_value = {"processed": 4, "to_upsert": 2, "upserted": 0}
        mock_tiingo.return_value = {"processed": 5, "to_upsert": 1, "upserted": 0}
        mock_ish.return_value = {"processed": 2, "to_upsert": 5, "upserted": 0}

        result = _run_all_steps(dry_run=True)

    mock_fx.assert_called_once_with(dry_run=True)
    mock_eodhd.assert_called_once_with(dry_run=True)
    mock_tiingo.assert_called_once_with(dry_run=True)
    mock_ish.assert_called_once_with(dry_run=True)

    assert result["dry_run"] is True
    assert result["fx"]["to_upsert"] == 3
    assert result["eodhd"]["to_upsert"] == 2
    assert result["tiingo"]["to_upsert"] == 1
    assert result["ishares"]["to_upsert"] == 5


def test_full_nightbatch_sequence_forwards_dry_run_false():
    """
    Verifies that dry_run=False is forwarded to all 4 individual update scripts
    when they are called in sequence.
    """
    with patch("src.nightbatch.fx_update.headless_load_missing_fx_rates") as mock_fx, \
         patch("src.nightbatch.eodhd_update.process_all_eodhd_assets") as mock_eodhd, \
         patch("src.nightbatch.tiingo_update.process_all_tiingo_assets") as mock_tiingo, \
         patch("src.nightbatch.ishares_update.process_all_ishares_assets") as mock_ish:

        mock_fx.return_value = {"loaded": 10, "upserted": 3, "dry_run": False}
        mock_eodhd.return_value = {"processed": 4, "upserted": 2}
        mock_tiingo.return_value = {"processed": 5, "upserted": 1}
        mock_ish.return_value = {"processed": 2, "upserted": 5}

        result = _run_all_steps(dry_run=False)

    mock_fx.assert_called_once_with(dry_run=False)
    mock_eodhd.assert_called_once_with(dry_run=False)
    mock_tiingo.assert_called_once_with(dry_run=False)
    mock_ish.assert_called_once_with(dry_run=False)

    assert result["dry_run"] is False
    assert result["fx"]["upserted"] == 3
    assert result["eodhd"]["upserted"] == 2
    assert result["tiingo"]["upserted"] == 1
    assert result["ishares"]["upserted"] == 5
