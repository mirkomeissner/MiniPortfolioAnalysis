import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.services.auth_service import (
    get_user_profile_record,
    login_user,
    register_user,
    update_email,
    update_password,
    update_username,
)


def test_get_user_profile_record_normalizes_profile_payload():
    repository = Mock()
    repository.get_user_profile.return_value = {
        "id": "user-1",
        "username": "alice",
        "email": "alice@example.com",
        "is_approved": True,
        "pending_email": "pending@example.com",
    }

    result = get_user_profile_record("user-1", repository=repository)

    repository.get_user_profile.assert_called_once_with("user-1")
    assert result == {
        "id": "user-1",
        "username": "alice",
        "email": "alice@example.com",
        "is_approved": True,
        "pending_email": "pending@example.com",
    }


def test_login_user_returns_profile_and_token_data():
    repository = Mock()
    repository.login.return_value = SimpleNamespace(
        session=SimpleNamespace(access_token="token-123"),
        user=SimpleNamespace(id="user-1", email="alice@example.com"),
    )
    repository.get_user_profile.return_value = {
        "username": "alice",
        "is_approved": True,
        "pending_email": None,
    }

    result = login_user("alice@example.com", "secret", repository=repository)

    repository.login.assert_called_once_with("alice@example.com", "secret")
    repository.get_user_profile.assert_called_once_with("user-1")
    assert result == {
        "authenticated": True,
        "access_token": "token-123",
        "user_id": "user-1",
        "username": "alice",
        "email": "alice@example.com",
        "is_approved": True,
        "pending_email": None,
    }


def test_register_user_duplicate_email_sends_notification_and_returns_success():
    repository = Mock()
    repository.check_existing_email.return_value = True

    with patch("backend.app.services.auth_service.send_duplicate_info_mail") as mail_mock:
        result = register_user("Alice@Example.com", "secret", "alice", repository=repository)

    repository.check_existing_email.assert_called_once_with("alice@example.com")
    mail_mock.assert_called_once_with("alice@example.com")
    assert result == {"user_created": True, "duplicate_email": True, "user_id": None}


def test_register_user_auto_approves_matching_admin_email():
    repository = Mock()
    repository.check_existing_email.return_value = False
    repository.register.return_value = SimpleNamespace(user=SimpleNamespace(id="user-1"))

    result = register_user(
        "admin@example.com",
        "secret",
        "admin",
        admin_emails=["admin@example.com"],
        repository=repository,
    )

    repository.approve_user.assert_called_once_with("user-1")
    assert result == {"user_created": True, "duplicate_email": False, "user_id": "user-1"}


def test_update_operations_forward_expected_payloads():
    repository = Mock()

    assert update_password("secret", repository=repository) == {"updated": True}
    assert update_username("alice", repository=repository) == {"updated": True, "username": "alice"}
    assert update_email("alice@example.com", repository=repository) == {
        "updated": True,
        "email": "alice@example.com",
    }

    repository.update_user.assert_any_call({"password": "secret"})
    repository.update_user.assert_any_call({"data": {"username": "alice"}})
    repository.update_user.assert_any_call({"email": "alice@example.com"})