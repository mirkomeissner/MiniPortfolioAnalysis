import os
import sys
from unittest.mock import MagicMock, patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_get_all_transactions_for_user_returns_data():
    from src.database import get_all_transactions_for_user

    response = MagicMock()
    response.data = [{"id": "AAA_20260630_000"}]

    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.execute.return_value = response

    table = MagicMock()
    table.select.return_value = query

    schema = MagicMock()
    schema.table.return_value = table

    client = MagicMock()
    client.schema.return_value = schema

    with patch("src.database._get_client", return_value=client):
        result = get_all_transactions_for_user("user-1")

    assert result == [{"id": "AAA_20260630_000"}]


def test_get_all_transactions_for_user_returns_empty_for_missing_user():
    from src.database import get_all_transactions_for_user

    assert get_all_transactions_for_user(None) == []