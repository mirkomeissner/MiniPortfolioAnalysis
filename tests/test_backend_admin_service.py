import os
import sys
from unittest.mock import Mock


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.services.admin_service import build_admin_users_df, get_admin_user_records, set_user_approval


def test_build_admin_users_df_returns_expected_columns_for_empty_input():
    df = build_admin_users_df([])

    assert list(df.columns) == [
        "ID",
        "Username",
        "Email",
        "Is Approved",
        "Created At",
        "Email Confirmed At",
    ]
    assert df.empty


def test_get_admin_user_records_returns_api_shape():
    repository = Mock()
    repository.get_all_users.return_value = [
        {
            "id": "user-1",
            "username": "alice",
            "email": "alice@example.com",
            "is_approved": True,
            "created_at": "2026-06-01T10:00:00",
            "email_confirmed_at": "2026-06-01T10:05:00",
        }
    ]

    result = get_admin_user_records(repository=repository)

    assert result == [
        {
            "id": "user-1",
            "username": "alice",
            "email": "alice@example.com",
            "is_approved": True,
            "created_at": "2026-06-01T10:00:00",
            "email_confirmed_at": "2026-06-01T10:05:00",
        }
    ]


def test_set_user_approval_calls_repository_and_returns_ack():
    repository = Mock()

    result = set_user_approval("user-1", True, repository=repository)

    repository.update_user_approval.assert_called_once_with("user-1", True)
    assert result == {"user_id": "user-1", "is_approved": True, "updated": True}