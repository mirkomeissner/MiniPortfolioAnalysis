import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.main import app


client = TestClient(app)


def test_login_endpoint_calls_service_with_payload():
    with patch(
        "backend.app.api.routers.auth.login_user",
        return_value={
            "authenticated": True,
            "access_token": "token-123",
            "user_id": "user-1",
            "username": "alice",
            "email": "alice@example.com",
            "is_approved": True,
            "pending_email": None,
        },
    ) as service_mock:
        response = client.post("/auth/login", json={"email": "alice@example.com", "password": "secret"})

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    service_mock.assert_called_once_with(email="alice@example.com", password="secret")


def test_register_endpoint_calls_service_with_payload():
    with patch(
        "backend.app.api.routers.auth.register_user",
        return_value={"user_created": True, "duplicate_email": False, "user_id": "user-1"},
    ) as service_mock:
        response = client.post(
            "/auth/register",
            json={
                "email": "alice@example.com",
                "password": "secret",
                "username": "alice",
                "admin_emails": ["admin@example.com"],
            },
        )

    assert response.status_code == 200
    assert response.json() == {"user_created": True, "duplicate_email": False, "user_id": "user-1"}
    service_mock.assert_called_once_with(
        email="alice@example.com",
        password="secret",
        username="alice",
        admin_emails=["admin@example.com"],
    )


def test_profile_endpoint_calls_service_with_user_id():
    with patch(
        "backend.app.api.routers.auth.get_user_profile_record",
        return_value={
            "id": "user-1",
            "username": "alice",
            "email": "alice@example.com",
            "is_approved": True,
            "pending_email": None,
        },
    ) as service_mock:
        response = client.get("/auth/profile", params={"user_id": "user-1"})

    assert response.status_code == 200
    assert response.json()["id"] == "user-1"
    service_mock.assert_called_once_with(user_id="user-1")


def test_update_endpoints_forward_expected_payloads():
    with patch("backend.app.api.routers.auth.update_password", return_value={"updated": True}) as password_mock:
        password_response = client.put("/auth/password", json={"password": "secret"})

    with patch(
        "backend.app.api.routers.auth.update_username",
        return_value={"updated": True, "username": "alice"},
    ) as username_mock:
        username_response = client.put("/auth/username", json={"username": "alice"})

    with patch(
        "backend.app.api.routers.auth.update_email",
        return_value={"updated": True, "email": "alice@example.com"},
    ) as email_mock:
        email_response = client.put("/auth/email", json={"email": "alice@example.com"})

    assert password_response.status_code == 200
    assert username_response.status_code == 200
    assert email_response.status_code == 200
    password_mock.assert_called_once_with("secret")
    username_mock.assert_called_once_with("alice")
    email_mock.assert_called_once_with("alice@example.com")


def test_logout_endpoint_calls_service():
    with patch("backend.app.api.routers.auth.logout_user", return_value={"logged_out": True}) as service_mock:
        response = client.post("/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"logged_out": True}
    service_mock.assert_called_once_with()