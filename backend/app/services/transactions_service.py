import pandas as pd

from backend.app.repositories.transactions_repository import TransactionsRepository


TRANSACTION_DISPLAY_COLUMNS = [
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

TRANSACTION_API_COLUMNS = {
    "Trade Date": "trade_date",
    "Account": "account",
    "ISIN": "isin",
    "Name": "name",
    "Type": "transaction_type",
    "Quantity": "quantity",
    "Settle Amount": "settle_amount",
    "Settle Curr": "settle_currency",
    "FX Rate": "fx_rate",
    "Amount (EUR)": "amount_eur",
    "Created At": "created_at",
    "Updated At": "updated_at",
    "Internal ID": "internal_id",
}

_DEFAULT_REPOSITORY = TransactionsRepository()


def get_transactions_df(user_id: str, repository: TransactionsRepository | None = None) -> pd.DataFrame:
    repo = repository or _DEFAULT_REPOSITORY
    return build_transactions_df(repo.get_all_transactions_for_user(user_id))


def build_transactions_df(raw_data) -> pd.DataFrame:
    if not raw_data:
        return pd.DataFrame([], columns=TRANSACTION_DISPLAY_COLUMNS)

    processed_data = []
    for row in raw_data:
        processed_row = row.copy()

        account_info = row.get("accounts")
        processed_row["account_label"] = (
            account_info.get("description")
            if account_info and account_info.get("description")
            else row.get("account_code")
        )
        processed_row["type_label"] = (
            row.get("ref_transaction_type", {}).get("label")
            if row.get("ref_transaction_type")
            else row.get("transaction_type_code")
        )
        processed_row["asset_name"] = (
            row.get("asset_static_data", {}).get("name")
            if row.get("asset_static_data")
            else row.get("isin")
        )
        processed_data.append(processed_row)

    df = pd.DataFrame(processed_data)

    column_mapping = {
        "date": "Trade Date",
        "account_label": "Account",
        "isin": "ISIN",
        "asset_name": "Name",
        "type_label": "Type",
        "quantity": "Quantity",
        "settle_amount": "Settle Amount",
        "settle_currency": "Settle Curr",
        "settle_fxrate": "FX Rate",
        "amount_eur": "Amount (EUR)",
        "created_at": "Created At",
        "updated_at": "Updated At",
        "id": "Internal ID",
    }

    df = df.rename(columns=column_mapping)
    existing_columns = [column for column in TRANSACTION_DISPLAY_COLUMNS if column in df.columns]
    df = df[existing_columns]

    if "Created At" in df.columns:
        df["Created At"] = pd.to_datetime(df["Created At"])
        df = df.sort_values(by="Created At", ascending=False)

    return df


def get_transaction_records(user_id: str, repository: TransactionsRepository | None = None) -> list[dict]:
    df = get_transactions_df(user_id, repository)
    if df.empty:
        return []

    api_df = df.rename(columns=TRANSACTION_API_COLUMNS)
    api_df = api_df.where(pd.notnull(api_df), None)
    if "trade_date" in api_df.columns:
        api_df["trade_date"] = pd.to_datetime(api_df["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return api_df.to_dict("records")


def create_transaction(transaction_data: dict, repository: TransactionsRepository | None = None) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    repo.save_transaction(transaction_data)
    return transaction_data


def create_transactions_bulk(transactions: list[dict], repository: TransactionsRepository | None = None) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    if not transactions:
        return {"saved_count": 0}

    repo.save_transactions_bulk(transactions)
    return {"saved_count": len(transactions)}


def get_user_import_settings(
    user_id: str,
    account_code: str,
    repository: TransactionsRepository | None = None,
) -> dict | None:
    repo = repository or _DEFAULT_REPOSITORY
    return repo.get_import_settings(user_id=user_id, account_code=account_code)


def save_user_import_settings(
    user_id: str,
    account_code: str,
    mapping_config: dict,
    repository: TransactionsRepository | None = None,
) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    repo.save_import_settings(user_id=user_id, account_code=account_code, mapping_config=mapping_config)
    return {
        "user_id": user_id,
        "account_code": account_code,
        "saved": True,
    }


def delete_all_transactions_for_user(user_id: str, repository: TransactionsRepository | None = None) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    repo.delete_all_transactions_for_user(user_id)
    return {
        "user_id": user_id,
        "deleted": True,
    }


def get_existing_ids_for_bulk_import(
    user_id: str,
    isins: list[str],
    dates: list[str],
    repository: TransactionsRepository | None = None,
) -> list[str]:
    repo = repository or _DEFAULT_REPOSITORY
    if not isins or not dates:
        return []
    return repo.get_existing_ids_for_bulk(user_id=user_id, isins=isins, dates=dates)


def get_missing_isins_for_import(isins: list[str], repository: TransactionsRepository | None = None) -> list[str]:
    repo = repository or _DEFAULT_REPOSITORY
    if not isins:
        return []
    return repo.get_missing_isins(isins)


def get_next_transaction_count_for_import(
    user_id: str,
    isin: str,
    date_str: str,
    repository: TransactionsRepository | None = None,
) -> int:
    repo = repository or _DEFAULT_REPOSITORY
    if not user_id or not isin or not date_str:
        return 1
    return repo.get_next_transaction_count(user_id=user_id, isin=isin, date_str=date_str)