import os
import sys
from unittest.mock import patch

import datetime

import pytest
import requests


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.utils.backend_api_client import (
    create_assets_bulk_via_backend,
    create_asset_via_backend,
    create_account_via_backend,
    create_transaction_via_backend,
    delete_all_transactions_via_backend,
    delete_account_via_backend,
    fetch_admin_users_via_backend,
    fetch_accounts_df,
    get_asset_price_start_date_via_backend,
    get_asset_price_start_dates_via_backend,
    fetch_assets_df,
    fetch_asset_prices_df,
    fetch_fx_rates_df,
    fetch_holdings_date_range,
    get_import_settings_via_backend,
    fetch_holdings_df,
    get_holdings_reorganization_status_via_backend,
    fetch_holdings_summary,
    fetch_reference_data_bundle,
    fetch_transactions_df,
    get_existing_ids_for_bulk_via_backend,
    get_next_transaction_count_via_backend,
    save_import_settings_via_backend,
    get_missing_isins_via_backend,
    reorganize_holdings_via_backend,
    save_transactions_bulk_via_backend,
    search_exchange_tickers_via_backend,
    update_user_approval_via_backend,
    update_account_via_backend,
    update_asset_start_dates_bulk_via_backend,
    update_asset_via_backend,
)


def test_fetch_asset_prices_df_uses_backend_api_when_configured():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        return_value=[
            {
                "isin": "AAA",
                "name": "Alpha Asset",
                "price_date": "2026-06-30",
                "price_close": 100.0,
                "price_currency": "USD",
                "dividend_cash": 0.5,
                "split_factor": 1.0,
            }
        ],
    ) as fetch_mock:
        df = fetch_asset_prices_df()

    fetch_mock.assert_called_once_with("/prices/assets")
    assert df.iloc[0].to_dict() == {
        "ISIN": "AAA",
        "Name": "Alpha Asset",
        "Price Date": "2026-06-30",
        "Price Close": 100.0,
        "Price Currency": "USD",
        "Dividend Cash": 0.5,
        "Split Factor": 1.0,
    }


def test_fetch_admin_users_via_backend_uses_api_when_configured():
    payload = [{"id": "user-1", "username": "alice", "email": "alice@example.com", "is_approved": True}]
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        return_value=payload,
    ) as fetch_mock:
        result = fetch_admin_users_via_backend()

    fetch_mock.assert_called_once_with("/admin/users")
    assert result == payload


def test_update_user_approval_via_backend_raises_on_request_error():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            update_user_approval_via_backend("user-1", True)


def test_fetch_assets_df_uses_backend_api_when_configured():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        return_value=[
            {
                "isin": "AAA",
                "name": "Alpha",
                "ticker": "ALP",
                "risk_currency": "USD",
                "instrument_type": "ETF",
                "asset_class": "Equity",
                "region": "North America",
                "sector": "Technology",
                "industry": "Software",
                "country": "US",
                "price_source": "Yahoo",
                "price_currency": "USD",
                "price_start_date": "2026-01-01",
                "closed_on": None,
                "created_at": "2026-01-01T00:00:00",
                "created_by": "admin",
                "updated_at": "2026-06-01T00:00:00",
                "updated_by": "admin2",
            }
        ],
    ) as fetch_mock:
        df = fetch_assets_df()

    fetch_mock.assert_called_once_with("/assets")
    assert df.iloc[0]["ISIN"] == "AAA"
    assert df.iloc[0]["Asset Class"] == "Equity"


def test_fetch_assets_df_normalizes_missing_closed_on_to_none():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        return_value=[
            {
                "isin": "AAA",
                "name": "Alpha",
                "closed_on": None,
            }
        ],
    ):
        records = fetch_assets_df().to_dict("records")

    assert records[0]["Closed On"] is None


def test_fetch_assets_df_passes_isins_filter_when_provided():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        return_value=[{"isin": "AAA", "name": "Alpha"}],
    ) as fetch_mock:
        df = fetch_assets_df(isins=["AAA", "BBB"])

    fetch_mock.assert_called_once_with("/assets", params={"isins": ["AAA", "BBB"]})
    assert df.iloc[0]["ISIN"] == "AAA"


def test_create_asset_via_backend_uses_api_when_configured():
    payload = {"isin": "AAA", "name": "Alpha"}
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        return_value=payload,
    ) as request_mock:
        result = create_asset_via_backend(payload)

    request_mock.assert_called_once_with("POST", "/assets", json=payload)
    assert result == payload


def test_create_assets_bulk_via_backend_uses_existing_asset_wrapper():
    asset_list = [{"isin": "AAA", "name": "Alpha"}, {"isin": "BBB", "name": "Beta"}]
    with patch("src.utils.backend_api_client.create_asset_via_backend", side_effect=asset_list) as create_mock:
        result = create_assets_bulk_via_backend(asset_list)

    assert create_mock.call_count == 2
    assert result == asset_list


def test_update_asset_via_backend_raises_on_request_error():
    payload = {"closed_on": None}
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            update_asset_via_backend("AAA", payload)


def test_get_asset_price_start_dates_via_backend_uses_filtered_assets_api():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        return_value=[
            {"isin": "AAA", "price_start_date": "2026-01-01"},
            {"isin": "BBB", "price_start_date": None},
        ],
    ) as fetch_mock:
        result = get_asset_price_start_dates_via_backend(["AAA", "BBB"])

    fetch_mock.assert_called_once_with("/assets", params={"isins": ["AAA", "BBB"]})
    assert result == {"AAA": "2026-01-01", "BBB": None}


def test_get_asset_price_start_date_via_backend_raises_on_request_error():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            get_asset_price_start_date_via_backend("AAA")


def test_search_exchange_tickers_via_backend_uses_api_when_configured():
    payload = [{"ticker_code": "ALP", "isin": "AAA"}]
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        return_value=payload,
    ) as fetch_mock:
        result = search_exchange_tickers_via_backend(isin="AAA", name="Alpha", active_only=False)

    fetch_mock.assert_called_once_with(
        "/assets/ticker-search",
        params={"isin": "AAA", "name": "Alpha", "active_only": False},
    )
    assert result == payload


def test_update_asset_start_dates_bulk_via_backend_uses_existing_update_wrapper():
    payload_list = [{"isin": "AAA", "price_start_date": "2026-01-01"}]
    with patch("src.utils.backend_api_client.update_asset_via_backend", return_value={"isin": "AAA"}) as update_mock:
        result = update_asset_start_dates_bulk_via_backend(payload_list)

    update_mock.assert_called_once_with("AAA", {"price_start_date": "2026-01-01"})
    assert result == [{"isin": "AAA"}]


def test_fetch_accounts_df_uses_backend_api_when_configured():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        return_value=[
            {"account_code": "ACC1", "description": "Main account"},
            {"account_code": "ACC2", "description": "Broker account"},
        ],
    ) as fetch_mock:
        df = fetch_accounts_df("user-1")

    fetch_mock.assert_called_once_with("/accounts", params={"user_id": "user-1"})
    assert df.to_dict("records") == [
        {"Account Code": "ACC1", "Description": "Main account"},
        {"Account Code": "ACC2", "Description": "Broker account"},
    ]


def test_fetch_accounts_df_normalizes_missing_description_to_none():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        return_value=[{"account_code": "ACC1", "description": None}],
    ):
        records = fetch_accounts_df("user-1").to_dict("records")

    assert records == [{"Account Code": "ACC1", "Description": None}]


def test_fetch_holdings_date_range_raises_on_request_error():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            fetch_holdings_date_range("user-1")


def test_create_account_via_backend_uses_api_when_configured():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        return_value={"account_code": "ACC3", "description": "New account"},
    ) as request_mock:
        result = create_account_via_backend("user-1", "ACC3", "New account")

    request_mock.assert_called_once_with(
        "POST",
        "/accounts",
        json={"user_id": "user-1", "account_code": "ACC3", "description": "New account"},
    )
    assert result == {"account_code": "ACC3", "description": "New account"}


def test_create_transaction_via_backend_raises_on_request_error():
    payload = {
        "user_id": "user-1",
        "id": "AAA_20260630_000",
        "account_code": "ACC1",
        "isin": "AAA",
        "date": "2026-06-30",
        "transaction_type_code": "BUY",
    }
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            create_transaction_via_backend(payload)


def test_save_transactions_bulk_via_backend_uses_api_when_configured():
    transaction_list = [{"id": "AAA_20260630_000", "user_id": "user-1"}]
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        return_value={"saved_count": 1},
    ) as request_mock:
        result = save_transactions_bulk_via_backend(transaction_list)

    request_mock.assert_called_once_with(
        "POST",
        "/transactions/bulk",
        json={"transactions": transaction_list},
    )
    assert result == {"saved_count": 1}


def test_get_import_settings_via_backend_raises_on_request_error():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            get_import_settings_via_backend("user-1", "ACC1")


def test_save_import_settings_via_backend_uses_api_when_configured():
    mapping_config = {"map_isin": "ISIN", "map_date": "Date"}
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        return_value={"user_id": "user-1", "account_code": "ACC1", "saved": True},
    ) as request_mock:
        result = save_import_settings_via_backend("user-1", "ACC1", mapping_config)

    request_mock.assert_called_once_with(
        "PUT",
        "/transactions/import-settings",
        json={"user_id": "user-1", "account_code": "ACC1", "mapping_config": mapping_config},
    )
    assert result == {"user_id": "user-1", "account_code": "ACC1", "saved": True}


def test_delete_all_transactions_via_backend_raises_on_request_error():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            delete_all_transactions_via_backend("user-1")


def test_get_existing_ids_for_bulk_via_backend_uses_api_when_configured():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        return_value={"ids": ["AAA_20260630_000"]},
    ) as request_mock:
        result = get_existing_ids_for_bulk_via_backend(
            "user-1",
            ["AAA"],
            ["2026-06-30"],
        )

    request_mock.assert_called_once_with(
        "POST",
        "/transactions/bulk-existing-ids",
        json={
            "user_id": "user-1",
            "isins": ["AAA"],
            "dates": ["2026-06-30"],
        },
    )
    assert result == ["AAA_20260630_000"]


def test_get_missing_isins_via_backend_raises_on_request_error():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            get_missing_isins_via_backend(["AAA", "BBB"])


def test_get_next_transaction_count_via_backend_raises_on_request_error():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            get_next_transaction_count_via_backend("user-1", "AAA", "2026-06-30")


def test_update_account_via_backend_raises_on_request_error():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            update_account_via_backend("user-1", "ACC1", "Updated")


def test_delete_account_via_backend_uses_api_when_configured():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        return_value={"account_code": "ACC1", "deleted": True},
    ) as request_mock:
        result = delete_account_via_backend("user-1", "ACC1")

    request_mock.assert_called_once_with("DELETE", "/accounts/ACC1", params={"user_id": "user-1"})
    assert result == {"account_code": "ACC1", "deleted": True}


def test_fetch_fx_rates_df_raises_on_request_error():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            fetch_fx_rates_df()


def test_fetch_holdings_df_uses_backend_api_when_configured():
    selected_date = datetime.date(2026, 6, 30)

    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        return_value=[
            {
                "user_id": "user-1",
                "account_code": "ACC1",
                "holding_date": "2026-06-30",
                "isin": "AAA",
                "quantity": 2.0,
                "price_currency": "USD",
                "price": 100.0,
                "valuation_in_price_currency": 200.0,
                "fx_to_eur": 1.1,
                "valuation_in_eur": 181.82,
                "asset_name": "Alpha Asset",
            }
        ],
    ) as fetch_mock:
        df = fetch_holdings_df("user-1", selected_date)

    fetch_mock.assert_called_once_with(
        "/holdings",
        params={"user_id": "user-1", "holding_date": "2026-06-30"},
    )
    assert df.iloc[0]["ISIN"] == "AAA"
    assert df.iloc[0]["Asset Name"] == "Alpha Asset"


def test_fetch_transactions_df_uses_backend_api_when_configured():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        return_value=[
            {
                "trade_date": "2026-06-30",
                "account": "Main Account",
                "isin": "AAA",
                "name": "Alpha Asset",
                "transaction_type": "Buy",
                "quantity": 2.0,
                "settle_amount": 100.0,
                "settle_currency": "USD",
                "fx_rate": 1.1,
                "amount_eur": 90.9,
                "created_at": "2026-06-30T12:00:00",
                "updated_at": "2026-06-30T12:30:00",
                "internal_id": "AAA_20260630_000",
            }
        ],
    ) as fetch_mock:
        df = fetch_transactions_df("user-1")

    fetch_mock.assert_called_once_with("/transactions", params={"user_id": "user-1"})
    assert df.iloc[0]["ISIN"] == "AAA"
    assert df.iloc[0]["Type"] == "Buy"


def test_fetch_holdings_summary_raises_on_request_error():
    selected_date = datetime.date(2026, 6, 30)

    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            fetch_holdings_summary("user-1", selected_date, "Asset Class")


def test_get_holdings_reorganization_status_via_backend_uses_api_when_configured():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        return_value={
            "user_id": "user-1",
            "last_transaction_modification": "2026-06-30T10:00:00+00:00",
            "last_reorganization": "2026-06-30T09:00:00+00:00",
            "account_count": 2,
        },
    ) as fetch_mock:
        result = get_holdings_reorganization_status_via_backend("user-1")

    fetch_mock.assert_called_once_with("/holdings/reorganization-status", params={"user_id": "user-1"})
    assert result["user_id"] == "user-1"
    assert result["account_count"] == 2


def test_reorganize_holdings_via_backend_raises_on_request_error():
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._request_json",
        side_effect=requests.RequestException("boom"),
    ):
        with pytest.raises(requests.RequestException):
            reorganize_holdings_via_backend("user-1", account_codes=["ACC1"], dry_run=False)


def test_fetch_reference_data_bundle_uses_backend_api_when_configured():
    payload = {
        "opt_asset": ["EQU (Equity)"],
        "opt_gics": ["TECH (Technology)"],
        "opt_region": ["NAM (North America)"],
        "opt_type": ["ETF (ETF)"],
        "opt_source": ["YAHOO (Yahoo)"],
        "opt_trans_types": ["BUY (Buy)"],
        "opt_accounts": ["ACC1 (Main)"],
        "opt_assets": ["AAA (Alpha)"],
        "db_region_map": {"US": "NAM"},
        "type_logic_map": {"BUY": {"quantity_sign": 1, "amount_sign": -1}},
    }
    with patch.dict(os.environ, {"BACKEND_API_URL": "http://backend.test"}, clear=False), patch(
        "src.utils.backend_api_client._fetch_json",
        return_value=payload,
    ) as fetch_mock:
        result = fetch_reference_data_bundle("user-1")

    fetch_mock.assert_called_once_with("/references/bootstrap", params={"user_id": "user-1"})
    assert result == payload