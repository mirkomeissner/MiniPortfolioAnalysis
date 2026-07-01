import os
import sys
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.utils.helpers import ensure_reference_data


def test_ensure_reference_data_populates_session_state_from_bundle():
    fake_streamlit = SimpleNamespace(
        session_state={"user_id": "user-1"},
        spinner=lambda _message: nullcontext(),
    )
    bundle = {
        "opt_asset": ["EQU (Equity)"],
        "opt_gics": ["TECH (Technology)"],
        "opt_region": ["NAM (North America)"],
        "opt_type": ["ETF (ETF)"],
        "opt_source": ["YAHOO (Yahoo)"],
        "opt_trans_types": ["BUY (Buy)"],
        "opt_accounts": ["ACC1 (Main)"],
        "opt_assets": ["AAA (Alpha)"],
        "db_region_map": {"US": "NAM"},
        "type_logic_map": {"BUY": {"quantity_sign": 1, "amount_sign": -1}},
    }

    with patch("src.utils.helpers.st", fake_streamlit), patch(
        "src.utils.helpers.fetch_reference_data_bundle",
        return_value=bundle,
    ) as fetch_mock:
        ensure_reference_data()

    fetch_mock.assert_called_once_with("user-1")
    assert fake_streamlit.session_state["opt_accounts"] == ["ACC1 (Main)"]
    assert fake_streamlit.session_state["type_logic_map"]["BUY"]["amount_sign"] == -1
    assert fake_streamlit.session_state["ref_data_loaded"] is True