import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.main import create_app


def test_app_startup_initializes_runtime_and_reports_health_state():
    with patch("backend.app.main.initialize_runtime_from_env", return_value=True) as init_mock:
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/health")

    init_mock.assert_called_once_with(strict=False)
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "runtime_initialized": True,
    }


def test_app_health_reports_uninitialized_runtime_when_env_is_missing():
    with patch("backend.app.main.initialize_runtime_from_env", return_value=False):
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "runtime_initialized": False,
    }


def test_app_middleware_binds_and_clears_request_context_from_headers():
    with patch("backend.app.main.initialize_runtime_from_env", return_value=True), patch(
        "backend.app.main.set_request_context"
    ) as set_context_mock, patch("backend.app.main.clear_request_context") as clear_context_mock:
        app = create_app()
        with TestClient(app) as client:
            response = client.get(
                "/health",
                headers={
                    "Authorization": "Bearer token-123",
                    "X-User-Id": "user-1",
                },
            )

    assert response.status_code == 200
    set_context_mock.assert_called_once_with(access_token="token-123", user_id="user-1")
    clear_context_mock.assert_called_once_with()