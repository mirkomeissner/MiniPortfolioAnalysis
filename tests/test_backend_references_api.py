import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.main import app


client = TestClient(app)


def test_reference_bootstrap_returns_service_payload():
    payload = {
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
    with patch(
        "backend.app.api.routers.references.get_reference_bootstrap",
        return_value=payload,
    ) as service_mock:
        response = client.get("/references/bootstrap", params={"user_id": "user-1"})

    assert response.status_code == 200
    assert response.json() == payload
    service_mock.assert_called_once_with(user_id="user-1")