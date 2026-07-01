import os
import sys
from unittest.mock import Mock, patch

import pytest
import requests


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.utils.backend_api_client import (
    _request_json,
    fetch_user_profile_via_backend,
    login_via_backend,
    logout_via_backend,
    register_user_via_backend,
    update_email_via_backend,
)


def test_request_json_attaches_runtime_context_headers():
    response = Mock()
    response.content = b'{"ok": true}'
    response.json.return_value = {"ok": True}
    response.raise_for_status.return_value = None

    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client.get_current_access_token",
        return_value="token-123",
    ), patch(
        "src.utils.backend_api_client.get_current_user_id",
        return_value="user-1",
    ), patch("src.utils.backend_api_client.requests.request", return_value=response) as request_mock:
        result = _request_json("GET", "/health")

    assert result == {"ok": True}
    request_mock.assert_called_once_with(
        "GET",
        "http://backend.test/health",
        params=None,
        json=None,
        headers={"Authorization": "Bearer token-123", "X-User-Id": "user-1"},
        timeout=10,
    )


def test_login_via_backend_uses_api_when_configured():
    payload = {"authenticated": True, "access_token": "token-123", "user_id": "user-1", "is_approved": True}
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        return_value=payload,
    ) as request_mock:
        result = login_via_backend("alice@example.com", "secret")

    request_mock.assert_called_once_with(
        "POST",
        "/auth/login",
        json={"email": "alice@example.com", "password": "secret"},
    )
    assert result == payload


def test_register_user_via_backend_raises_on_request_error():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            register_user_via_backend("alice@example.com", "secret", "alice", admin_emails=["admin@example.com"])


def test_fetch_user_profile_via_backend_uses_api_when_configured():
    payload = {"id": "user-1", "username": "alice", "email": "alice@example.com", "is_approved": True}
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        return_value=payload,
    ) as fetch_mock:
        result = fetch_user_profile_via_backend("user-1")

    fetch_mock.assert_called_once_with("/auth/profile", params={"user_id": "user-1"})
    assert result == payload


def test_logout_via_backend_raises_on_request_error():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            logout_via_backend()


def test_request_json_requires_backend_api_url():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="BACKEND_API_URL is required"):
            _request_json("GET", "/health")


def test_update_email_via_backend_uses_api_when_configured():
    payload = {"updated": True, "email": "alice@example.com"}
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        return_value=payload,
    ) as request_mock:
        result = update_email_via_backend("alice@example.com")

    request_mock.assert_called_once_with("PUT", "/auth/email", json={"email": "alice@example.com"})
    assert result == payload