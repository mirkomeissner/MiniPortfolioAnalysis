import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.main import app


client = TestClient(app)


def test_list_admin_users_returns_service_records():
    with patch(
        "backend.app.api.routers.admin.get_admin_user_records",
        return_value=[
            {
                "id": "user-1",
                "username": "alice",
                "email": "alice@example.com",
                "is_approved": True,
                "created_at": "2026-06-01T10:00:00",
                "email_confirmed_at": "2026-06-01T10:05:00",
            }
        ],
    ) as service_mock:
        response = client.get("/admin/users")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "user-1"
    service_mock.assert_called_once_with()


def test_update_user_approval_calls_service_with_payload():
    with patch(
        "backend.app.api.routers.admin.set_user_approval",
        return_value={"user_id": "user-1", "is_approved": False, "updated": True},
    ) as service_mock:
        response = client.put("/admin/users/user-1/approval", json={"is_approved": False})

    assert response.status_code == 200
    assert response.json() == {"user_id": "user-1", "is_approved": False, "updated": True}
    service_mock.assert_called_once_with(user_id="user-1", is_approved=False)