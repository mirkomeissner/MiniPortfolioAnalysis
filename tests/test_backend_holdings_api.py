import datetime
import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.main import app


client = TestClient(app)


def test_get_holdings_date_range_calls_service_and_serializes_dates():
    with patch(
        "backend.app.api.routers.holdings.get_holdings_date_range",
        return_value={
            "user_id": "user-1",
            "first_date": datetime.date(2026, 1, 10),
            "last_date": datetime.date(2026, 6, 30),
        },
    ) as service_mock:
        response = client.get("/holdings/date-range", params={"user_id": "user-1"})

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "user-1",
        "first_date": "2026-01-10",
        "last_date": "2026-06-30",
    }
    service_mock.assert_called_once_with(user_id="user-1")


def test_list_holdings_returns_service_records():
    with patch(
        "backend.app.api.routers.holdings.get_holdings_records",
        return_value=[
            {
                "user_id": "user-1",
                "account_code": "ACC1",
                "holding_date": "2026-06-30",
                "isin": "AAA",
                "quantity": 2.0,
                "price_currency": "USD",
                "price": 100.0,
                "valuation_in_price_currency": 200.0,
                "fx_to_eur": 1.1,
                "valuation_in_eur": 181.82,
                "asset_name": "Alpha Asset",
                "asset_ticker": "ALP",
                "asset_risk_currency": "USD",
                "asset_type": "ETF",
                "asset_class": "Equity",
                "asset_region": "North America",
                "asset_sector": "Technology",
                "asset_industry": "Software",
                "asset_country": "US",
            }
        ],
    ):
        response = client.get("/holdings", params={"user_id": "user-1", "holding_date": "2026-06-30"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "user_id": "user-1",
            "account_code": "ACC1",
            "holding_date": "2026-06-30",
            "isin": "AAA",
            "quantity": 2.0,
            "price_currency": "USD",
            "price": 100.0,
            "valuation_in_price_currency": 200.0,
            "fx_to_eur": 1.1,
            "valuation_in_eur": 181.82,
            "asset_name": "Alpha Asset",
            "asset_ticker": "ALP",
            "asset_risk_currency": "USD",
            "asset_type": "ETF",
            "asset_class": "Equity",
            "asset_region": "North America",
            "asset_sector": "Technology",
            "asset_industry": "Software",
            "asset_country": "US",
        }
    ]


def test_list_holdings_requires_query_params():
    response = client.get("/holdings")

    assert response.status_code == 422


def test_get_reorganization_status_calls_service_and_normalizes_response():
    with patch(
        "backend.app.api.routers.holdings.get_holdings_reorganization_status",
        return_value={
            "user_id": "user-1",
            "last_transaction_modification": "2026-06-30T10:00:00+00:00",
            "last_reorganization": "2026-06-30T09:00:00+00:00",
            "account_count": 2,
        },
    ) as service_mock:
        response = client.get("/holdings/reorganization-status", params={"user_id": "user-1"})

    assert response.status_code == 200
    assert response.json()["user_id"] == "user-1"
    assert response.json()["account_count"] == 2
    service_mock.assert_called_once_with(user_id="user-1")


def test_run_reorganization_calls_service_with_payload():
    payload = {
        "user_id": "user-1",
        "account_codes": ["ACC1"],
        "dry_run": False,
    }
    with patch(
        "backend.app.api.routers.holdings.run_holdings_reorganization",
        return_value={
            "user_id": "user-1",
            "relevant_accounts_count": 1,
            "transactions_scanned": 10,
            "snapshots_generated": 5,
            "rows_deleted": 1,
            "rows_inserted": 2,
            "rows_updated": 3,
            "rows_unchanged": 4,
            "reorg_timestamp_written": True,
            "reorg_timestamp": "2026-06-30T10:15:00+00:00",
            "dry_run": False,
        },
    ) as service_mock:
        response = client.post("/holdings/reorganize", json=payload)

    assert response.status_code == 200
    assert response.json()["user_id"] == "user-1"
    assert response.json()["rows_inserted"] == 2
    service_mock.assert_called_once_with(
        user_id="user-1",
        account_codes=["ACC1"],
        dry_run=False,
    )