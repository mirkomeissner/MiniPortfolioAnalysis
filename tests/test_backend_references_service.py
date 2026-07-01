import os
import sys
from unittest.mock import Mock


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.services.references_service import get_reference_bootstrap


def test_reference_bootstrap_aggregates_repository_calls():
    repository = Mock()
    repository.get_ref_options.side_effect = [
        ["EQU (Equity)"],
        ["TECH (Technology)"],
        ["NAM (North America)"],
        ["ETF (ETF)"],
        ["YAHOO (Yahoo)"],
        ["BUY (Buy)"],
    ]
    repository.get_account_ref_options.return_value = ["ACC1 (Main)"]
    repository.get_asset_ref_options.return_value = ["AAA (Alpha)"]
    repository.get_country_region_map.return_value = {"US": "NAM"}
    repository.get_transaction_type_logic.return_value = {"BUY": {"quantity_sign": 1, "amount_sign": -1}}

    result = get_reference_bootstrap("user-1", repository=repository)

    assert result["opt_accounts"] == ["ACC1 (Main)"]
    assert result["opt_assets"] == ["AAA (Alpha)"]
    assert result["db_region_map"] == {"US": "NAM"}
    assert result["type_logic_map"]["BUY"]["quantity_sign"] == 1
    repository.get_account_ref_options.assert_called_once_with("user-1")