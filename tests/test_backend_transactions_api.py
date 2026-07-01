import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.main import app


client = TestClient(app)


def test_list_transactions_returns_service_records():
    with patch(
        "backend.app.api.routers.transactions.get_transaction_records",
        return_value=[
            {
                "trade_date": "2026-06-30",
                "account": "Main Account",
                "isin": "AAA",
                "name": "Alpha Asset",
                "transaction_type": "Buy",
                "quantity": 2.0,
                "settle_amount": 100.0,
                "settle_currency": "USD",
                "fx_rate": 1.1,
                "amount_eur": 90.9,
                "created_at": "2026-06-30T12:00:00",
                "updated_at": "2026-06-30T12:30:00",
                "internal_id": "AAA_20260630_000",
            }
        ],
    ):
        response = client.get("/transactions", params={"user_id": "user-1"})

    assert response.status_code == 200
    assert response.json()[0]["isin"] == "AAA"
    assert response.json()[0]["transaction_type"] == "Buy"


def test_list_transactions_requires_user_id():
    response = client.get("/transactions")

    assert response.status_code == 422


def test_create_transaction_calls_service_with_payload():
    payload = {
        "user_id": "user-1",
        "account_code": "ACC1",
        "isin": "AAA",
        "date": "2026-06-30",
        "transaction_type_code": "BUY",
        "quantity": 2.0,
        "settle_amount": 100.0,
        "settle_currency": "USD",
        "settle_fxrate": 1.1,
        "amount_eur": 90.9,
    }
    service_result = {
        **payload,
        "id": "AAA_20260630_000",
    }
    with patch(
        "backend.app.api.routers.transactions.create_transaction",
        return_value=service_result,
    ) as service_mock:
        response = client.post("/transactions", json=payload)

    assert response.status_code == 200
    assert response.json() == service_result
    service_mock.assert_called_once_with(payload)


def test_get_import_settings_calls_service_with_query_params():
    with patch(
        "backend.app.api.routers.transactions.get_user_import_settings",
        return_value={"map_isin": "ISIN"},
    ) as service_mock:
        response = client.get(
            "/transactions/import-settings",
            params={"user_id": "user-1", "account_code": "ACC1"},
        )

    assert response.status_code == 200
    assert response.json() == {"mapping_config": {"map_isin": "ISIN"}}
    service_mock.assert_called_once_with(user_id="user-1", account_code="ACC1")


def test_save_import_settings_calls_service_with_payload():
    payload = {
        "user_id": "user-1",
        "account_code": "ACC1",
        "mapping_config": {"map_isin": "ISIN", "map_date": "Date"},
    }
    with patch(
        "backend.app.api.routers.transactions.save_user_import_settings",
        return_value={"user_id": "user-1", "account_code": "ACC1", "saved": True},
    ) as service_mock:
        response = client.put("/transactions/import-settings", json=payload)

    assert response.status_code == 200
    assert response.json() == {"user_id": "user-1", "account_code": "ACC1", "saved": True}
    service_mock.assert_called_once_with(
        user_id="user-1",
        account_code="ACC1",
        mapping_config={"map_isin": "ISIN", "map_date": "Date"},
    )


def test_delete_transactions_calls_service_with_user_id():
    with patch(
        "backend.app.api.routers.transactions.delete_all_transactions_for_user",
        return_value={"user_id": "user-1", "deleted": True},
    ) as service_mock:
        response = client.delete("/transactions", params={"user_id": "user-1"})

    assert response.status_code == 200
    assert response.json() == {"user_id": "user-1", "deleted": True}
    service_mock.assert_called_once_with(user_id="user-1")


def test_missing_isins_calls_service_with_payload():
    payload = {"isins": ["AAA", "BBB"]}
    with patch(
        "backend.app.api.routers.transactions.get_missing_isins_for_import",
        return_value=["BBB"],
    ) as service_mock:
        response = client.post("/transactions/missing-isins", json=payload)

    assert response.status_code == 200
    assert response.json() == {"missing_isins": ["BBB"]}
    service_mock.assert_called_once_with(["AAA", "BBB"])


def test_import_preview_calls_service_with_payload():
    payload = {
        "user_id": "user-1",
        "account_code": "ACC1",
        "csv_content": "isin,date,type,quantity,settle_amount,settle_currency\nAAA,2026-06-30,BUY,2,100,USD",
        "mapping_config": {
            "map_isin": "isin",
            "map_date": "date",
            "map_type": "type",
            "map_quantity": "quantity",
            "map_settle_amount": "settle_amount",
            "map_settle_currency": "settle_currency",
        },
    }
    service_result = {
        "rows": [
            {
                "user_id": "user-1",
                "account_code": "ACC1",
                "isin": "AAA",
                "date": "2026-06-30",
                "transaction_type_code": "BUY",
                "quantity": 2.0,
                "settle_amount": 100.0,
                "settle_currency": "USD",
                "settle_fxrate": 1.0,
                "amount_eur": 100.0,
            }
        ],
        "missing_isins": [],
        "existing_ids": [],
        "duplicate_overlap_count": 0,
    }
    with patch(
        "backend.app.api.routers.transactions.build_transaction_import_preview",
        return_value=service_result,
    ) as service_mock:
        response = client.post("/transactions/import-preview", json=payload)

    assert response.status_code == 200
    assert response.json() == service_result
    service_mock.assert_called_once_with(
        user_id="user-1",
        account_code="ACC1",
        csv_content=payload["csv_content"],
        mapping_config=payload["mapping_config"],
    )


def test_import_bulk_calls_service_with_payload():
    payload = {
        "user_id": "user-1",
        "rows": [
            {
                "user_id": "user-1",
                "account_code": "ACC1",
                "isin": "AAA",
                "date": "2026-06-30",
                "transaction_type_code": "BUY",
                "quantity": 2.0,
                "settle_amount": 100.0,
                "settle_currency": "USD",
                "settle_fxrate": 1.0,
                "amount_eur": 100.0,
            }
        ],
        "duplicate_strategy": "skip",
    }

    with patch(
        "backend.app.api.routers.transactions.import_transactions_from_preview",
        return_value={"saved_count": 1, "skipped_overlap_count": 0},
    ) as service_mock:
        response = client.post("/transactions/import-bulk", json=payload)

    assert response.status_code == 200
    assert response.json() == {"saved_count": 1, "skipped_overlap_count": 0}
    service_mock.assert_called_once_with(
        user_id="user-1",
        rows=payload["rows"],
        duplicate_strategy="skip",
    )