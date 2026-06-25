import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _mock_supabase(rows):
    execute_result = MagicMock()
    execute_result.data = rows

    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.execute.return_value = execute_result

    table = MagicMock()
    table.select.return_value = query

    schema = MagicMock()
    schema.table.return_value = table

    client = MagicMock()
    client.schema.return_value = schema
    return client


def test_get_user_holdings_reorganization_status_aggregates_latest_values():
    from src.database import get_user_holdings_reorganization_status

    client = _mock_supabase(
        [
            {
                "user_id": "user-1",
                "account_code": "A1",
                "last_transaction_modification": "2026-06-24T10:00:00+00:00",
                "last_reorganization": "2026-06-24T11:00:00+00:00",
            },
            {
                "user_id": "user-1",
                "account_code": "A2",
                "last_transaction_modification": "2026-06-25T09:00:00+00:00",
                "last_reorganization": "2026-06-25T08:00:00+00:00",
            },
        ]
    )

    with patch("src.database._get_client", return_value=client):
        status = get_user_holdings_reorganization_status("user-1")

    assert status is not None
    assert status["account_count"] == 2
    assert status["last_transaction_modification"] == datetime(2026, 6, 25, 9, 0, tzinfo=timezone.utc)
    assert status["last_reorganization"] == datetime(2026, 6, 25, 8, 0, tzinfo=timezone.utc)


def test_get_user_holdings_reorganization_status_handles_missing_rows():
    from src.database import get_user_holdings_reorganization_status

    client = _mock_supabase([])

    with patch("src.database._get_client", return_value=client):
        status = get_user_holdings_reorganization_status("user-1")

    assert status is None


def test_insert_user_holdings_reorganization_inserts_current_user():
    from src.database import insert_user_holdings_reorganization

    execute_result = MagicMock()

    insert_call = MagicMock()
    insert_call.execute.return_value = execute_result

    table = MagicMock()
    table.insert.return_value = insert_call

    schema = MagicMock()
    schema.table.return_value = table

    client = MagicMock()
    client.schema.return_value = schema

    with patch("src.database.get_admin_client", return_value=client), patch(
        "src.database.get_current_user_id", return_value="user-1"
    ):
        result = insert_user_holdings_reorganization()

    assert result is execute_result
    table.insert.assert_called_once_with({"user_id": "user-1"})


def test_holdings_ui_state_hides_button_when_transaction_timestamp_is_missing():
    from src.components.holdings_analysis import _get_holdings_reorganization_ui_state

    ui_state = _get_holdings_reorganization_ui_state(
        {
            "last_transaction_modification": None,
            "last_reorganization": datetime(2026, 6, 25, 8, 0, tzinfo=timezone.utc),
        }
    )

    assert ui_state["visible"] is False
    assert ui_state["info_text"] is None


def test_holdings_ui_state_shows_button_with_empty_info_when_reorganization_is_missing():
    from src.components.holdings_analysis import _get_holdings_reorganization_ui_state

    ui_state = _get_holdings_reorganization_ui_state(
        {
            "last_transaction_modification": datetime(2026, 6, 25, 9, 0, tzinfo=timezone.utc),
            "last_reorganization": None,
        }
    )

    assert ui_state["visible"] is True
    assert ui_state["label"] == "Reorganization of Holdings"
    assert ui_state["disabled"] is False
    assert ui_state["info_text"] == ""