import datetime
import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_get_user_holdings_min_date_returns_earliest_date_from_rows():
    from src.database import get_user_holdings_min_date

    response = MagicMock()
    response.data = [{"holding_date": "2026-01-10"}]

    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.execute.return_value = response

    table = MagicMock()
    table.select.return_value = query

    schema = MagicMock()
    schema.table.return_value = table

    client = MagicMock()
    client.schema.return_value = schema

    with patch("src.database._get_client", return_value=client), patch("src.database.get_current_user_id", return_value="user-1"):
        result = get_user_holdings_min_date()

    assert result == datetime.date(2026, 1, 10)


def test_get_user_holdings_min_date_returns_none_when_no_data():
    from src.database import get_user_holdings_min_date

    response = MagicMock()
    response.data = []

    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.execute.return_value = response

    table = MagicMock()
    table.select.return_value = query

    schema = MagicMock()
    schema.table.return_value = table

    client = MagicMock()
    client.schema.return_value = schema

    with patch("src.database._get_client", return_value=client), patch("src.database.get_current_user_id", return_value="user-1"):
        result = get_user_holdings_min_date()

    assert result is None


def test_render_holdings_view_renders_date_picker_with_expected_bounds():
    from src.components.holdings_analysis import render_holdings_view

    fixed_today = datetime.date(2026, 6, 26)
    first_date = datetime.date(2026, 1, 10)
    expected_last_date = datetime.date(2026, 6, 25)

    class FixedDate(datetime.date):
        @classmethod
        def today(cls):
            return fixed_today

    with patch("src.components.holdings_analysis.get_user_holdings_min_date", return_value=first_date), patch(
        "src.components.holdings_analysis.datetime.date", FixedDate
    ), patch("src.components.holdings_analysis.st.title"), patch(
        "src.components.holdings_analysis.st.caption"
    ), patch("src.components.holdings_analysis.st.write"), patch(
        "src.components.holdings_analysis.st.info"
    ) as info_mock, patch("src.components.holdings_analysis.st.date_input", return_value=expected_last_date) as date_input_mock, patch(
        "src.components.holdings_analysis.fetch_holdings_df",
        return_value=pd.DataFrame(),
    ):
        render_holdings_view()

    info_mock.assert_not_called()
    date_input_mock.assert_called_once()
    args, kwargs = date_input_mock.call_args
    assert args[0] == "Holdings Date"
    assert kwargs["min_value"] == first_date
    assert kwargs["max_value"] == expected_last_date
    assert kwargs["value"] == expected_last_date
    assert kwargs["key"] == "holdings_selected_date"


def test_render_holdings_view_shows_info_when_no_holdings_exist():
    from src.components.holdings_analysis import render_holdings_view

    with patch("src.components.holdings_analysis.get_user_holdings_min_date", return_value=None), patch(
        "src.components.holdings_analysis.st.title"
    ), patch("src.components.holdings_analysis.st.info") as info_mock, patch(
        "src.components.holdings_analysis.st.date_input"
    ) as date_input_mock:
        render_holdings_view()

    info_mock.assert_called_once_with("No holdings are available yet.")
    date_input_mock.assert_not_called()
