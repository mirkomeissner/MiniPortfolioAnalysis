import pandas as pd
import csv
import io
import re

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
    if not transaction_data.get("id"):
        user_id = transaction_data.get("user_id")
        isin = transaction_data.get("isin")
        date_str = transaction_data.get("date")
        count = get_next_transaction_count_for_import(
            user_id=user_id,
            isin=isin,
            date_str=date_str,
            repository=repo,
        )
        transaction_data = {
            **transaction_data,
            "id": f"{isin}_{str(date_str).replace('-', '')}_{str(count).zfill(3)}",
        }

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


def _extract_code(value: str) -> str:
    if not isinstance(value, str):
        return str(value)
    return value.split(" (")[0].strip()


def _parse_number(value: str, field: str, row_number: int) -> float:
    normalized = str(value).replace(",", ".").strip()
    try:
        return float(normalized)
    except Exception as exc:
        raise ValueError(f"Invalid {field} in CSV row {row_number}.") from exc


def _normalize_date(value: str, row_number: int) -> str:
    parsed = pd.to_datetime(str(value).strip(), errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Invalid date in CSV row {row_number}.")
    return parsed.date().isoformat()


def _duplicate_pair_set(existing_ids: list[str]) -> set[str]:
    pairs = set()
    for transaction_id in existing_ids:
        match = re.match(r"^(.+?)_(\d{8})_\d+$", transaction_id)
        if not match:
            continue
        isin = match.group(1)
        date_token = match.group(2)
        normalized_date = f"{date_token[:4]}-{date_token[4:6]}-{date_token[6:8]}"
        pairs.add(f"{isin}|{normalized_date}")
    return pairs


def build_transaction_import_preview(
    user_id: str,
    account_code: str,
    csv_content: str,
    mapping_config: dict,
    repository: TransactionsRepository | None = None,
) -> dict:
    repo = repository or _DEFAULT_REPOSITORY

    required_mapping_keys = [
        "map_isin",
        "map_date",
        "map_type",
        "map_quantity",
        "map_settle_amount",
        "map_settle_currency",
    ]
    for key in required_mapping_keys:
        if not mapping_config.get(key):
            raise ValueError(f"Please complete required import mapping: {key}")

    reader = csv.DictReader(io.StringIO(csv_content))
    headers = reader.fieldnames or []
    if not headers:
        raise ValueError("CSV file must contain a header row.")

    for key in required_mapping_keys:
        column_name = mapping_config[key]
        if column_name not in headers:
            raise ValueError(f"Mapped column '{column_name}' for {key} is not present in CSV.")

    rows = []
    for idx, raw_row in enumerate(reader, start=2):
        isin = (raw_row.get(mapping_config["map_isin"]) or "").strip()
        date_value = raw_row.get(mapping_config["map_date"]) or ""
        type_value = raw_row.get(mapping_config["map_type"]) or ""
        quantity_value = raw_row.get(mapping_config["map_quantity"]) or ""
        settle_amount_value = raw_row.get(mapping_config["map_settle_amount"]) or ""
        settle_currency = (raw_row.get(mapping_config["map_settle_currency"]) or "").strip().upper()

        if not isin or not str(date_value).strip() or not settle_currency:
            raise ValueError(f"Missing required values in CSV row {idx}.")

        settle_fx_key = mapping_config.get("map_settle_fxrate")
        amount_eur_key = mapping_config.get("map_amount_eur")
        settle_fx_value = raw_row.get(settle_fx_key) if settle_fx_key else None
        amount_eur_value = raw_row.get(amount_eur_key) if amount_eur_key else None

        quantity = _parse_number(quantity_value, "quantity", idx)
        settle_amount = _parse_number(settle_amount_value, "settle_amount", idx)
        settle_fxrate = _parse_number(settle_fx_value, "settle_fxrate", idx) if settle_fx_value not in (None, "") else 1.0

        if amount_eur_value not in (None, ""):
            amount_eur = _parse_number(amount_eur_value, "amount_eur", idx)
        else:
            if settle_fxrate == 0:
                raise ValueError(f"Invalid settle_fxrate in CSV row {idx}.")
            amount_eur = settle_amount / settle_fxrate

        rows.append(
            {
                "user_id": user_id,
                "account_code": account_code,
                "isin": isin,
                "date": _normalize_date(date_value, idx),
                "transaction_type_code": _extract_code(str(type_value)),
                "quantity": quantity,
                "settle_amount": settle_amount,
                "settle_currency": settle_currency,
                "settle_fxrate": settle_fxrate,
                "amount_eur": amount_eur,
            }
        )

    unique_isins = sorted({row["isin"] for row in rows})
    unique_dates = sorted({row["date"] for row in rows})
    missing_isins = get_missing_isins_for_import(unique_isins, repository=repo)
    existing_ids = get_existing_ids_for_bulk_import(
        user_id=user_id,
        isins=unique_isins,
        dates=unique_dates,
        repository=repo,
    )

    duplicate_pairs = _duplicate_pair_set(existing_ids)
    duplicate_overlap_count = len([row for row in rows if f"{row['isin']}|{row['date']}" in duplicate_pairs])

    return {
        "rows": rows,
        "missing_isins": missing_isins,
        "existing_ids": existing_ids,
        "duplicate_overlap_count": duplicate_overlap_count,
    }


def import_transactions_from_preview(
    user_id: str,
    rows: list[dict],
    duplicate_strategy: str,
    repository: TransactionsRepository | None = None,
) -> dict:
    repo = repository or _DEFAULT_REPOSITORY

    if not rows:
        return {
            "saved_count": 0,
            "skipped_overlap_count": 0,
        }

    unique_isins = sorted({row.get("isin") for row in rows if row.get("isin")})
    unique_dates = sorted({row.get("date") for row in rows if row.get("date")})
    existing_ids = get_existing_ids_for_bulk_import(
        user_id=user_id,
        isins=unique_isins,
        dates=unique_dates,
        repository=repo,
    )
    duplicate_pairs = _duplicate_pair_set(existing_ids)

    to_save = []
    skipped_overlap_count = 0
    next_count_cache: dict[str, int] = {}

    for row in rows:
        isin = row.get("isin")
        date_str = row.get("date")
        if not isin or not date_str:
            continue

        pair_key = f"{isin}|{date_str}"
        if duplicate_strategy == "skip" and pair_key in duplicate_pairs:
            skipped_overlap_count += 1
            continue

        count = next_count_cache.get(pair_key)
        if count is None:
            count = get_next_transaction_count_for_import(
                user_id=user_id,
                isin=isin,
                date_str=date_str,
                repository=repo,
            )
        next_count_cache[pair_key] = count + 1

        transaction = {
            "user_id": user_id,
            "id": f"{isin}_{date_str.replace('-', '')}_{str(count).zfill(3)}",
            "account_code": row.get("account_code"),
            "isin": isin,
            "date": date_str,
            "transaction_type_code": row.get("transaction_type_code"),
            "quantity": row.get("quantity"),
            "settle_amount": row.get("settle_amount"),
            "settle_currency": row.get("settle_currency"),
            "settle_fxrate": row.get("settle_fxrate"),
            "amount_eur": row.get("amount_eur"),
        }
        to_save.append(transaction)

    create_transactions_bulk(to_save, repository=repo)
    return {
        "saved_count": len(to_save),
        "skipped_overlap_count": skipped_overlap_count,
    }