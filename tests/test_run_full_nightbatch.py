import os
import sys
from unittest.mock import patch

# Ensure project root is on sys.path so 'src' package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.nightbatch import run_full_nightbatch


def test_run_full_nightbatch_forwards_dry_run_to_fx_and_ishares():
    with patch("src.nightbatch.run_full_nightbatch.fx_updater.headless_load_missing_fx_rates") as mock_fx, \
         patch("src.nightbatch.run_full_nightbatch.process_all_ishares_assets") as mock_ish:
        mock_fx.return_value = {"loaded": 10, "to_upsert": 3, "dry_run": True}
        mock_ish.return_value = {"processed": 2, "to_upsert": 5, "upserted": 0}

        summary = run_full_nightbatch.run_full_nightbatch(dry_run=True)

    mock_fx.assert_called_once_with(dry_run=True)
    mock_ish.assert_called_once_with(dry_run=True)

    assert summary["dry_run"] is True
    assert summary["fx"]["to_upsert"] == 3
    assert summary["ishares"]["to_upsert"] == 5


def test_run_full_nightbatch_default_non_dry_run():
    with patch("src.nightbatch.run_full_nightbatch.fx_updater.headless_load_missing_fx_rates") as mock_fx, \
         patch("src.nightbatch.run_full_nightbatch.process_all_ishares_assets") as mock_ish:
        mock_fx.return_value = {"loaded": 10, "upserted": 3, "dry_run": False}
        mock_ish.return_value = {"processed": 2, "upserted": 5}

        summary = run_full_nightbatch.run_full_nightbatch()

    mock_fx.assert_called_once_with(dry_run=False)
    mock_ish.assert_called_once_with(dry_run=False)

    assert summary["dry_run"] is False
    assert summary["fx"]["upserted"] == 3
    assert summary["ishares"]["upserted"] == 5
