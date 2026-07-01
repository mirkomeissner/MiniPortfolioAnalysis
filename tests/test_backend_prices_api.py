import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.main import app


client = TestClient(app)


def test_list_asset_prices_returns_service_records():
    with patch(
        "backend.app.api.routers.prices.get_asset_price_records",
        return_value=[
            {
                "isin": "TEST123",
                "name": "Test Asset",
                "price_date": "2026-06-30",
                "price_close": 101.5,
                "price_currency": "USD",
                "dividend_cash": 0.5,
                "split_factor": 1.0,
            }
        ],
    ):
        response = client.get("/prices/assets")

    assert response.status_code == 200
    assert response.json() == [
        {
            "isin": "TEST123",
            "name": "Test Asset",
            "price_date": "2026-06-30",
            "price_close": 101.5,
            "price_currency": "USD",
            "dividend_cash": 0.5,
            "split_factor": 1.0,
        }
    ]


def test_list_fx_rates_returns_service_records():
    with patch(
        "backend.app.api.routers.prices.get_fx_rate_records",
        return_value=[
            {
                "currency": "USD",
                "date": "2026-06-30",
                "exchange_rate": 1.1723,
                "date_original": "2026-06-30",
                "created_at": "2026-07-01T00:00:00",
                "updated_at": "2026-07-01T00:00:00",
            }
        ],
    ):
        response = client.get("/prices/fx")

    assert response.status_code == 200
    assert response.json() == [
        {
            "currency": "USD",
            "date": "2026-06-30",
            "exchange_rate": 1.1723,
            "date_original": "2026-06-30",
            "created_at": "2026-07-01T00:00:00",
            "updated_at": "2026-07-01T00:00:00",
        }
    ]