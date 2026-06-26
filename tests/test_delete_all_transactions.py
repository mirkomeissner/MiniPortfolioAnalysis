import os
import sys
from unittest.mock import MagicMock, call, patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _build_delete_query(execute_side_effect=None):
    execute_mock = MagicMock(side_effect=execute_side_effect)

    eq_query = MagicMock()
    eq_query.execute = execute_mock

    delete_query = MagicMock()
    delete_query.eq.return_value = eq_query

    table_query = MagicMock()
    table_query.delete.return_value = delete_query
    return table_query, execute_mock


def test_delete_all_transactions_deletes_transactions_and_holdings_for_user():
    from src.database import delete_all_transactions

    tx_result = MagicMock()
    holdings_result = MagicMock()

    tx_table, tx_execute = _build_delete_query()
    tx_execute.return_value = tx_result

    holdings_table, holdings_execute = _build_delete_query()
    holdings_execute.return_value = holdings_result

    schema = MagicMock()
    schema.table.side_effect = lambda table_name: {
        "transactions": tx_table,
        "incremental_holdings": holdings_table,
    }[table_name]

    client = MagicMock()
    client.schema.return_value = schema

    with patch("src.database._get_client", return_value=client):
        result = delete_all_transactions("user-1")

    assert result is holdings_result
    assert client.schema.call_args_list == [call("public"), call("public")]
    assert schema.table.call_args_list == [
        call("transactions"),
        call("incremental_holdings"),
    ]
    tx_table.delete.assert_called_once()
    tx_table.delete.return_value.eq.assert_called_once_with("user_id", "user-1")
    tx_execute.assert_called_once()
    holdings_table.delete.assert_called_once()
    holdings_table.delete.return_value.eq.assert_called_once_with("user_id", "user-1")
    holdings_execute.assert_called_once()


def test_delete_all_transactions_propagates_error_from_holdings_delete():
    from src.database import delete_all_transactions

    tx_table, tx_execute = _build_delete_query()
    tx_execute.return_value = MagicMock()

    holdings_error = RuntimeError("holdings delete failed")
    holdings_table, _ = _build_delete_query(execute_side_effect=holdings_error)

    schema = MagicMock()
    schema.table.side_effect = lambda table_name: {
        "transactions": tx_table,
        "incremental_holdings": holdings_table,
    }[table_name]

    client = MagicMock()
    client.schema.return_value = schema

    with patch("src.database._get_client", return_value=client):
        try:
            delete_all_transactions("user-1")
            raised = None
        except Exception as exc:  # pragma: no cover - explicit propagation assertion
            raised = exc

    assert raised is holdings_error
    tx_execute.assert_called_once()
    holdings_table.delete.assert_called_once()
