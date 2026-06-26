import os
import sys
from contextlib import nullcontext
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


def test_reorganize_incremental_holdings_calls_rpc_and_normalizes_summary():
    from src.database import reorganize_incremental_holdings

    execute_result = MagicMock()
    execute_result.data = {
        "user_id": "user-1",
        "relevant_accounts_count": 2,
        "transactions_scanned": 15,
        "snapshots_generated": 8,
        "rows_deleted": 1,
        "rows_inserted": 3,
        "rows_updated": 2,
        "rows_unchanged": 4,
        "reorg_timestamp_written": True,
        "reorg_timestamp": "2026-06-26T10:00:00+00:00",
        "dry_run": False,
    }

    rpc_call = MagicMock()
    rpc_call.execute.return_value = execute_result

    client = MagicMock()
    client.rpc.return_value = rpc_call

    with patch("src.database._get_client", return_value=client), patch("src.database.get_current_user_id", return_value="user-1"):
        result = reorganize_incremental_holdings()

    client.rpc.assert_called_once_with(
        "reorganize_incremental_holdings",
        {"p_user_id": "user-1", "p_account_codes": None, "p_dry_run": False},
    )
    assert result["user_id"] == "user-1"
    assert result["relevant_accounts_count"] == 2
    assert result["rows_inserted"] == 3
    assert result["rows_updated"] == 2
    assert result["rows_deleted"] == 1
    assert result["reorg_timestamp_written"] is True
    assert result["reorg_timestamp"] == datetime(2026, 6, 26, 10, 0, tzinfo=timezone.utc)


def test_reorganize_incremental_holdings_returns_default_when_rpc_data_is_none():
    from src.database import reorganize_incremental_holdings

    execute_result = MagicMock()
    execute_result.data = None

    rpc_call = MagicMock()
    rpc_call.execute.return_value = execute_result

    client = MagicMock()
    client.rpc.return_value = rpc_call

    with patch("src.database._get_client", return_value=client):
        result = reorganize_incremental_holdings("user-1")

    assert result["user_id"] == "user-1"
    assert result["relevant_accounts_count"] == 0
    assert result["reorg_timestamp_written"] is False


def test_render_holdings_view_shows_success_summary_when_reorganization_runs():
    from src.components.holdings_analysis import render_holdings_view

    status = {
        "last_transaction_modification": datetime(2026, 6, 26, 9, 0, tzinfo=timezone.utc),
        "last_reorganization": datetime(2026, 6, 26, 8, 0, tzinfo=timezone.utc),
    }

    with patch("src.components.holdings_analysis.get_user_holdings_reorganization_status", return_value=status), patch(
        "src.components.holdings_analysis.reorganize_incremental_holdings",
        return_value={"relevant_accounts_count": 1, "rows_inserted": 2, "rows_updated": 3, "rows_deleted": 4},
    ), patch("src.components.holdings_analysis.st.columns", return_value=(nullcontext(), nullcontext())), patch(
        "src.components.holdings_analysis.st.button", return_value=True
    ), patch("src.components.holdings_analysis.st.success") as success_mock, patch(
        "src.components.holdings_analysis.st.info"
    ) as info_mock, patch("src.components.holdings_analysis.st.rerun") as rerun_mock, patch(
        "src.components.holdings_analysis.st.write"
    ):
        render_holdings_view()

    info_mock.assert_not_called()
    success_mock.assert_called_once()
    success_text = success_mock.call_args[0][0]
    assert "accounts=1" in success_text
    assert "inserted=2" in success_text
    assert "updated=3" in success_text
    assert "deleted=4" in success_text
    rerun_mock.assert_called_once()


def test_render_holdings_view_shows_info_when_no_account_requires_reorganization():
    from src.components.holdings_analysis import render_holdings_view

    status = {
        "last_transaction_modification": datetime(2026, 6, 26, 9, 0, tzinfo=timezone.utc),
        "last_reorganization": datetime(2026, 6, 26, 8, 0, tzinfo=timezone.utc),
    }

    with patch("src.components.holdings_analysis.get_user_holdings_reorganization_status", return_value=status), patch(
        "src.components.holdings_analysis.reorganize_incremental_holdings",
        return_value={"relevant_accounts_count": 0},
    ), patch("src.components.holdings_analysis.st.columns", return_value=(nullcontext(), nullcontext())), patch(
        "src.components.holdings_analysis.st.button", return_value=True
    ), patch("src.components.holdings_analysis.st.success") as success_mock, patch(
        "src.components.holdings_analysis.st.info"
    ) as info_mock, patch("src.components.holdings_analysis.st.rerun") as rerun_mock, patch(
        "src.components.holdings_analysis.st.write"
    ):
        render_holdings_view()

    success_mock.assert_not_called()
    info_mock.assert_called_once_with("No account requires holdings reorganization.")
    rerun_mock.assert_called_once()


def test_render_holdings_view_shows_error_when_reorganization_fails():
    from src.components.holdings_analysis import render_holdings_view

    status = {
        "last_transaction_modification": datetime(2026, 6, 26, 9, 0, tzinfo=timezone.utc),
        "last_reorganization": datetime(2026, 6, 26, 8, 0, tzinfo=timezone.utc),
    }

    with patch("src.components.holdings_analysis.get_user_holdings_reorganization_status", return_value=status), patch(
        "src.components.holdings_analysis.reorganize_incremental_holdings",
        side_effect=RuntimeError("boom"),
    ), patch("src.components.holdings_analysis.st.columns", return_value=(nullcontext(), nullcontext())), patch(
        "src.components.holdings_analysis.st.button", return_value=True
    ), patch("src.components.holdings_analysis.st.error") as error_mock, patch(
        "src.components.holdings_analysis.st.rerun"
    ) as rerun_mock, patch("src.components.holdings_analysis.st.write"):
        render_holdings_view()

    error_mock.assert_called_once()
    assert "Could not reorganize holdings" in error_mock.call_args[0][0]
    rerun_mock.assert_not_called()


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