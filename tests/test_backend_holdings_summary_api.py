import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.main import app


client = TestClient(app)


def test_get_holdings_summary_returns_service_payload():
    with patch(
        "backend.app.api.routers.holdings.get_holdings_summary",
        return_value={
            "pie_dimension": "Asset Class",
            "total_valuation_eur": 300.0,
            "items": [
                {"label": "Equity", "valuation_eur": 100.0, "color_hex": "#111111"},
                {"label": "Bond", "valuation_eur": 200.0, "color_hex": "#222222"},
            ],
        },
    ):
        response = client.get(
            "/holdings/summary",
            params={
                "user_id": "user-1",
                "holding_date": "2026-06-30",
                "pie_dimension": "Asset Class",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "pie_dimension": "Asset Class",
        "total_valuation_eur": 300.0,
        "items": [
            {"label": "Equity", "valuation_eur": 100.0, "color_hex": "#111111"},
            {"label": "Bond", "valuation_eur": 200.0, "color_hex": "#222222"},
        ],
    }