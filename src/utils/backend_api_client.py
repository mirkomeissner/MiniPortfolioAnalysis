import os

import pandas as pd
import requests

from src.runtime_context import get_current_access_token, get_current_user_id


def get_backend_api_base_url() -> str | None:
    base_url = os.environ.get("BACKEND_API_URL", "").strip()
    return base_url.rstrip("/") if base_url else None


def _require_backend_api_base_url() -> str:
    base_url = get_backend_api_base_url()
    if not base_url:
        raise RuntimeError("BACKEND_API_URL is required. Configure FastAPI URL to run in API-only mode.")
    return base_url


def _build_request_headers() -> dict[str, str]:
    headers = {}
    access_token = get_current_access_token()
    user_id = get_current_user_id()
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if user_id:
        headers["X-User-Id"] = user_id
    return headers


def _normalize_dataframe_nulls(df: pd.DataFrame) -> pd.DataFrame:
    return df.astype(object).where(pd.notnull(df), None)


def _fetch_json(path: str, params: dict | None = None):
    return _request_json("GET", path, params=params)


def _request_json(method: str, path: str, params: dict | None = None, json: dict | None = None):
    base_url = _require_backend_api_base_url()

    try:
        response = requests.request(
            method,
            f"{base_url}{path}",
            params=params,
            json=json,
            headers=_build_request_headers() or None,
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        response = getattr(exc, "response", None)
        detail = None
        if response is not None:
            detail = (response.text or "").strip() or None
        if detail:
            raise RuntimeError(detail) from exc
        raise RuntimeError(f"Backend API request failed: {exc}") from exc

    if not response.content:
        return None
    return response.json()


def _build_asset_prices_df_from_api(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(
            [],
            columns=["ISIN", "Name", "Price Date", "Price Close", "Price Currency", "Dividend Cash", "Split Factor"],
        )

    df = df.rename(
        columns={
            "isin": "ISIN",
            "name": "Name",
            "price_date": "Price Date",
            "price_close": "Price Close",
            "price_currency": "Price Currency",
            "dividend_cash": "Dividend Cash",
            "split_factor": "Split Factor",
        }
    )
    column_order = ["ISIN", "Name", "Price Date", "Price Close", "Price Currency", "Dividend Cash", "Split Factor"]
    available_columns = [column for column in column_order if column in df.columns]
    return _normalize_dataframe_nulls(df[available_columns])


def _build_fx_rates_df_from_api(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(
            [],
            columns=["Currency", "Date", "Exchange Rate", "Date Original", "Created At", "Updated At"],
        )

    df = df.rename(
        columns={
            "currency": "Currency",
            "date": "Date",
            "exchange_rate": "Exchange Rate",
            "date_original": "Date Original",
            "created_at": "Created At",
            "updated_at": "Updated At",
        }
    )
    return _normalize_dataframe_nulls(df)


def _build_holdings_df_from_api(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(
            [],
            columns=[
                "User ID",
                "Account Code",
                "Holding Date",
                "ISIN",
                "Quantity",
                "Price Currency",
                "Price",
                "Valuation (Price Curr)",
                "FX to EUR",
                "Valuation (EUR)",
                "Asset Name",
                "Asset Ticker",
                "Asset Risk Currency",
                "Asset Type",
                "Asset Class",
                "Asset Region",
                "Asset Sector",
                "Asset Industry",
                "Asset Country",
            ],
        )

    df = df.rename(
        columns={
            "user_id": "User ID",
            "account_code": "Account Code",
            "holding_date": "Holding Date",
            "isin": "ISIN",
            "quantity": "Quantity",
            "price_currency": "Price Currency",
            "price": "Price",
            "valuation_in_price_currency": "Valuation (Price Curr)",
            "fx_to_eur": "FX to EUR",
            "valuation_in_eur": "Valuation (EUR)",
            "asset_name": "Asset Name",
            "asset_ticker": "Asset Ticker",
            "asset_risk_currency": "Asset Risk Currency",
            "asset_type": "Asset Type",
            "asset_class": "Asset Class",
            "asset_region": "Asset Region",
            "asset_sector": "Asset Sector",
            "asset_industry": "Asset Industry",
            "asset_country": "Asset Country",
        }
    )

    if "Holding Date" in df.columns:
        df["Holding Date"] = pd.to_datetime(df["Holding Date"], errors="coerce")

    preferred_columns = [
        "User ID",
        "Account Code",
        "Holding Date",
        "ISIN",
        "Quantity",
        "Price Currency",
        "Price",
        "Valuation (Price Curr)",
        "FX to EUR",
        "Valuation (EUR)",
        "Asset Name",
        "Asset Ticker",
        "Asset Risk Currency",
        "Asset Type",
        "Asset Class",
        "Asset Region",
        "Asset Sector",
        "Asset Industry",
        "Asset Country",
    ]
    available_columns = [column for column in preferred_columns if column in df.columns]
    return _normalize_dataframe_nulls(df[available_columns])


def _build_assets_df_from_api(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(
            [],
            columns=[
                "ISIN",
                "Name",
                "Ticker",
                "Risk Currency",
                "Type",
                "Asset Class",
                "Region",
                "Sector",
                "Industry",
                "Country",
                "Price Source",
                "Price Currency",
                "Price Start Date",
                "Closed On",
                "Created At",
                "Created By",
                "Updated At",
                "Updated By",
            ],
        )

    df = df.rename(
        columns={
            "isin": "ISIN",
            "name": "Name",
            "ticker": "Ticker",
            "risk_currency": "Risk Currency",
            "instrument_type": "Type",
            "asset_class": "Asset Class",
            "region": "Region",
            "sector": "Sector",
            "industry": "Industry",
            "country": "Country",
            "price_source": "Price Source",
            "price_currency": "Price Currency",
            "price_start_date": "Price Start Date",
            "closed_on": "Closed On",
            "created_at": "Created At",
            "created_by": "Created By",
            "updated_at": "Updated At",
            "updated_by": "Updated By",
        }
    )

    preferred_columns = [
        "ISIN",
        "Name",
        "Ticker",
        "Risk Currency",
        "Type",
        "Asset Class",
        "Region",
        "Sector",
        "Industry",
        "Country",
        "Price Source",
        "Price Currency",
        "Price Start Date",
        "Closed On",
        "Created At",
        "Created By",
        "Updated At",
        "Updated By",
    ]
    available_columns = [column for column in preferred_columns if column in df.columns]
    return _normalize_dataframe_nulls(df[available_columns])


def _build_accounts_df_from_api(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame([], columns=["Account Code", "Description"])

    df = df.rename(columns={"account_code": "Account Code", "description": "Description"})
    available_columns = [column for column in ["Account Code", "Description"] if column in df.columns]
    return _normalize_dataframe_nulls(df[available_columns])


def _build_transactions_df_from_api(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(
            [],
            columns=[
                "Trade Date",
                "Account",
                "ISIN",
                "Name",
                "Type",
                "Quantity",
                "Settle Amount",
                "Settle Curr",
                "FX Rate",
                "Amount (EUR)",
                "Created At",
                "Updated At",
                "Internal ID",
            ],
        )

    df = df.rename(
        columns={
            "trade_date": "Trade Date",
            "account": "Account",
            "isin": "ISIN",
            "name": "Name",
            "transaction_type": "Type",
            "quantity": "Quantity",
            "settle_amount": "Settle Amount",
            "settle_currency": "Settle Curr",
            "fx_rate": "FX Rate",
            "amount_eur": "Amount (EUR)",
            "created_at": "Created At",
            "updated_at": "Updated At",
            "internal_id": "Internal ID",
        }
    )

    if "Created At" in df.columns:
        df["Created At"] = pd.to_datetime(df["Created At"], errors="coerce")
        df = df.sort_values(by="Created At", ascending=False)

    preferred_columns = [
        "Trade Date",
        "Account",
        "ISIN",
        "Name",
        "Type",
        "Quantity",
        "Settle Amount",
        "Settle Curr",
        "FX Rate",
        "Amount (EUR)",
        "Created At",
        "Updated At",
        "Internal ID",
    ]
    available_columns = [column for column in preferred_columns if column in df.columns]
    return _normalize_dataframe_nulls(df[available_columns])


def fetch_asset_prices_df() -> pd.DataFrame:
    records = _fetch_json("/prices/assets")
    return _build_asset_prices_df_from_api(records or [])


def fetch_fx_rates_df() -> pd.DataFrame:
    records = _fetch_json("/prices/fx")
    return _build_fx_rates_df_from_api(records or [])


def fetch_assets_df(isins: list[str] | None = None) -> pd.DataFrame:
    records = _fetch_json("/assets", params={"isins": isins}) if isins else _fetch_json("/assets")
    return _build_assets_df_from_api(records or [])


def login_via_backend(email: str, password: str) -> dict:
    payload = {"email": email, "password": password}
    result = _request_json("POST", "/auth/login", json=payload)
    return result or {
        "authenticated": False,
        "access_token": None,
        "user_id": None,
        "username": None,
        "email": email,
        "is_approved": False,
        "pending_email": None,
    }


def register_user_via_backend(email: str, password: str, username: str, admin_emails: list[str] | None = None) -> dict:
    payload = {
        "email": email,
        "password": password,
        "username": username,
        "admin_emails": admin_emails or [],
    }
    return _request_json("POST", "/auth/register", json=payload)


def fetch_user_profile_via_backend(user_id: str) -> dict | None:
    params = {"user_id": user_id}
    return _fetch_json("/auth/profile", params=params)


def logout_via_backend():
    return _request_json("POST", "/auth/logout")


def update_password_via_backend(password: str):
    payload = {"password": password}
    return _request_json("PUT", "/auth/password", json=payload)


def update_username_via_backend(username: str):
    payload = {"username": username}
    return _request_json("PUT", "/auth/username", json=payload)


def update_email_via_backend(email: str):
    payload = {"email": email}
    return _request_json("PUT", "/auth/email", json=payload)


def create_asset_via_backend(asset_data: dict):
    return _request_json("POST", "/assets", json=asset_data)


def update_asset_via_backend(isin: str, update_data: dict):
    return _request_json("PUT", f"/assets/{isin}", json=update_data)


def create_assets_bulk_via_backend(asset_list: list[dict]):
    results = []
    for asset_data in asset_list:
        results.append(create_asset_via_backend(asset_data))
    return results


def get_asset_price_start_dates_via_backend(isins: list[str]):
    if not isins:
        return {}

    records = _fetch_json("/assets", params={"isins": isins})
    return {record["isin"]: record.get("price_start_date") for record in (records or []) if record.get("isin")}


def get_asset_price_start_date_via_backend(isin: str):
    if not isin:
        return None

    records = _fetch_json("/assets", params={"isins": [isin]})
    for record in records or []:
        if record.get("isin") == isin:
            return record.get("price_start_date")
    return None


def update_asset_start_dates_bulk_via_backend(payload_list: list[dict]):
    if not payload_list:
        return None

    results = []
    for item in payload_list:
        results.append(update_asset_via_backend(item["isin"], {"price_start_date": item["price_start_date"]}))
    return results


def search_exchange_tickers_via_backend(isin: str | None = None, name: str | None = None, active_only: bool = True):
    params = {
        "isin": isin,
        "name": name,
        "active_only": active_only,
    }
    return _fetch_json("/assets/ticker-search", params=params)


def fetch_accounts_df(user_id: str) -> pd.DataFrame:
    params = {"user_id": user_id}
    records = _fetch_json("/accounts", params=params)
    return _build_accounts_df_from_api(records or [])


def create_account_via_backend(user_id: str, account_code: str, description: str):
    payload = {
        "user_id": user_id,
        "account_code": account_code,
        "description": description,
    }
    return _request_json("POST", "/accounts", json=payload)


def update_account_via_backend(user_id: str, account_code: str, description: str):
    payload = {
        "user_id": user_id,
        "description": description,
    }
    return _request_json("PUT", f"/accounts/{account_code}", json=payload)


def delete_account_via_backend(user_id: str, account_code: str):
    params = {"user_id": user_id}
    return _request_json("DELETE", f"/accounts/{account_code}", params=params)


def fetch_holdings_df(user_id: str, selected_date) -> pd.DataFrame:
    params = {"user_id": user_id, "holding_date": selected_date.isoformat()}
    records = _fetch_json("/holdings", params=params)
    return _build_holdings_df_from_api(records or [])


def fetch_holdings_date_range(user_id: str) -> dict:
    params = {"user_id": user_id}
    result = _fetch_json("/holdings/date-range", params=params)
    if result is None:
        return {
            "user_id": user_id,
            "first_date": None,
            "last_date": None,
        }

    return {
        **result,
        "first_date": pd.to_datetime(result.get("first_date"), errors="coerce").date()
        if result.get("first_date")
        else None,
        "last_date": pd.to_datetime(result.get("last_date"), errors="coerce").date()
        if result.get("last_date")
        else None,
    }


def fetch_transactions_df(user_id: str) -> pd.DataFrame:
    params = {"user_id": user_id}
    records = _fetch_json("/transactions", params=params)
    return _build_transactions_df_from_api(records or [])


def create_transaction_via_backend(transaction_data: dict):
    return _request_json("POST", "/transactions", json=transaction_data)


def get_import_settings_via_backend(user_id: str, account_code: str):
    params = {"user_id": user_id, "account_code": account_code}
    result = _fetch_json("/transactions/import-settings", params=params)
    return result.get("mapping_config") if result else None


def save_import_settings_via_backend(user_id: str, account_code: str, mapping_config: dict):
    payload = {
        "user_id": user_id,
        "account_code": account_code,
        "mapping_config": mapping_config,
    }
    return _request_json("PUT", "/transactions/import-settings", json=payload)


def delete_all_transactions_via_backend(user_id: str):
    params = {"user_id": user_id}
    return _request_json("DELETE", "/transactions", params=params)


def get_missing_isins_via_backend(isins: list[str]):
    payload = {"isins": isins}
    result = _request_json("POST", "/transactions/missing-isins", json=payload)
    return result.get("missing_isins", []) if result else []


def import_transactions_bulk_via_backend(user_id: str, rows: list[dict], duplicate_strategy: str = "allow"):
    payload = {
        "user_id": user_id,
        "rows": rows,
        "duplicate_strategy": duplicate_strategy,
    }
    return _request_json("POST", "/transactions/import-bulk", json=payload)


def fetch_holdings_summary(user_id: str, selected_date, pie_dimension: str) -> dict:
    params = {
        "user_id": user_id,
        "holding_date": selected_date.isoformat(),
        "pie_dimension": pie_dimension,
    }
    summary = _fetch_json("/holdings/summary", params=params)
    return summary or {
        "pie_dimension": pie_dimension,
        "total_valuation_eur": 0.0,
        "items": [],
    }


def get_holdings_reorganization_status_via_backend(user_id: str):
    params = {"user_id": user_id}
    status = _fetch_json("/holdings/reorganization-status", params=params)
    if status is None:
        return None

    return {
        **status,
        "last_transaction_modification": pd.to_datetime(
            status.get("last_transaction_modification"),
            errors="coerce",
        )
        if status.get("last_transaction_modification")
        else None,
        "last_reorganization": pd.to_datetime(
            status.get("last_reorganization"),
            errors="coerce",
        )
        if status.get("last_reorganization")
        else None,
    }


def reorganize_holdings_via_backend(user_id: str, account_codes: list[str] | None = None, dry_run: bool = False):
    payload = {
        "user_id": user_id,
        "account_codes": account_codes,
        "dry_run": dry_run,
    }
    summary = _request_json("POST", "/holdings/reorganize", json=payload)
    if summary is None:
        return None

    return {
        **summary,
        "reorg_timestamp": pd.to_datetime(summary.get("reorg_timestamp"), errors="coerce")
        if summary.get("reorg_timestamp")
        else None,
    }


def fetch_reference_data_bundle(user_id: str) -> dict:
    params = {"user_id": user_id}
    result = _fetch_json("/references/bootstrap", params=params)
    return result or {
        "opt_asset": [],
        "opt_gics": [],
        "opt_region": [],
        "opt_type": [],
        "opt_source": [],
        "opt_trans_types": [],
        "opt_accounts": [],
        "opt_assets": [],
        "db_region_map": {},
        "type_logic_map": {},
    }


def fetch_admin_users_via_backend() -> list[dict]:
    result = _fetch_json("/admin/users")
    return result or []


def update_user_approval_via_backend(user_id: str, is_approved: bool):
    payload = {"is_approved": is_approved}
    return _request_json("PUT", f"/admin/users/{user_id}/approval", json=payload)
