import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.main import app


client = TestClient(app)


def test_list_accounts_returns_service_records():
    with patch(
        "backend.app.api.routers.accounts.get_account_records",
        return_value=[{"account_code": "ACC1", "description": "Main account"}],
    ):
        response = client.get("/accounts", params={"user_id": "user-1"})

    assert response.status_code == 200
    assert response.json() == [{"account_code": "ACC1", "description": "Main account"}]


def test_list_accounts_requires_user_id():
    response = client.get("/accounts")

    assert response.status_code == 422


def test_create_account_calls_service():
    with patch(
        "backend.app.api.routers.accounts.create_account",
        return_value={"account_code": "ACC3", "description": "New account"},
    ) as service_mock:
        response = client.post(
            "/accounts",
            json={
                "user_id": "user-1",
                "account_code": "ACC3",
                "description": "New account",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"account_code": "ACC3", "description": "New account"}
    service_mock.assert_called_once_with(
        user_id="user-1",
        account_code="ACC3",
        description="New account",
    )


def test_update_account_calls_service():
    with patch(
        "backend.app.api.routers.accounts.update_account_description",
        return_value={"account_code": "ACC1", "description": "Updated"},
    ) as service_mock:
        response = client.put(
            "/accounts/ACC1",
            json={
                "user_id": "user-1",
                "description": "Updated",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"account_code": "ACC1", "description": "Updated"}
    service_mock.assert_called_once_with(
        user_id="user-1",
        account_code="ACC1",
        description="Updated",
    )


def test_delete_account_calls_service():
    with patch(
        "backend.app.api.routers.accounts.remove_account",
        return_value={"account_code": "ACC1", "deleted": True},
    ) as service_mock:
        response = client.delete("/accounts/ACC1", params={"user_id": "user-1"})

    assert response.status_code == 200
    assert response.json() == {"account_code": "ACC1", "deleted": True}
    service_mock.assert_called_once_with(user_id="user-1", account_code="ACC1")