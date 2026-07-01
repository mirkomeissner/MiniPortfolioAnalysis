import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.main import app


client = TestClient(app)


def test_list_assets_returns_service_records():
    with patch(
        "backend.app.api.routers.assets.get_asset_records",
        return_value=[
            {
                "isin": "AAA",
                "name": "Alpha",
                "ticker": "ALP",
                "risk_currency": "USD",
                "instrument_type": "ETF",
                "asset_class": "Equity",
                "region": "North America",
                "sector": "Technology",
                "industry": "Software",
                "country": "US",
                "price_source": "Yahoo",
                "price_currency": "USD",
                "price_start_date": "2026-01-01",
                "closed_on": None,
                "created_at": "2026-01-01T00:00:00",
                "created_by": "admin",
                "updated_at": "2026-06-01T00:00:00",
                "updated_by": "admin2",
            }
        ],
    ):
        response = client.get("/assets")

    assert response.status_code == 200
    assert response.json()[0]["isin"] == "AAA"
    assert response.json()[0]["asset_class"] == "Equity"


def test_list_assets_passes_optional_isins_filter():
    with patch(
        "backend.app.api.routers.assets.get_asset_records",
        return_value=[{"isin": "AAA", "name": "Alpha"}],
    ) as service_mock:
        response = client.get("/assets", params=[("isins", "AAA"), ("isins", "BBB")])

    assert response.status_code == 200
    service_mock.assert_called_once_with(isins=["AAA", "BBB"])


def test_ticker_search_passes_query_parameters_to_service():
    with patch(
        "backend.app.api.routers.assets.search_exchange_ticker_records",
        return_value=[{"ticker_code": "ALP", "isin": "AAA"}],
    ) as service_mock:
        response = client.get(
            "/assets/ticker-search",
            params={"isin": "AAA", "name": "Alpha", "active_only": "false"},
        )

    assert response.status_code == 200
    assert response.json() == [{"ticker_code": "ALP", "isin": "AAA"}]
    service_mock.assert_called_once_with(isin="AAA", name="Alpha", active_only=False)


def test_create_asset_calls_service_with_payload():
    with patch(
        "backend.app.api.routers.assets.create_asset",
        return_value={"isin": "BBB", "name": "Beta"},
    ) as service_mock:
        response = client.post(
            "/assets",
            json={
                "isin": "BBB",
                "name": "Beta",
            },
        )

    assert response.status_code == 200
    assert response.json()["isin"] == "BBB"
    service_mock.assert_called_once_with({"isin": "BBB", "name": "Beta"})


def test_update_asset_calls_service_with_isin_and_payload():
    with patch(
        "backend.app.api.routers.assets.update_asset",
        return_value={"isin": "AAA", "closed_on": None},
    ) as service_mock:
        response = client.put(
            "/assets/AAA",
            json={
                "closed_on": None,
            },
        )

    assert response.status_code == 200
    assert response.json() == {"isin": "AAA", "closed_on": None}
    service_mock.assert_called_once_with("AAA", {"closed_on": None})