import pandas as pd

from backend.app.repositories.accounts_repository import AccountsRepository


ACCOUNT_DISPLAY_COLUMNS = ["Account Code", "Description"]

ACCOUNT_API_COLUMNS = {
    "Account Code": "account_code",
    "Description": "description",
}

_DEFAULT_REPOSITORY = AccountsRepository()


def get_accounts_df(user_id: str, repository: AccountsRepository | None = None) -> pd.DataFrame:
    repo = repository or _DEFAULT_REPOSITORY
    return build_accounts_df(repo.get_all_accounts(user_id))


def build_accounts_df(raw_data) -> pd.DataFrame:
    df = pd.DataFrame(raw_data)
    if df.empty:
        return pd.DataFrame([], columns=ACCOUNT_DISPLAY_COLUMNS)

    df = df.rename(columns={"account_code": "Account Code", "description": "Description"})
    available_columns = [column for column in ACCOUNT_DISPLAY_COLUMNS if column in df.columns]
    df = df[available_columns]
    return df.astype(object).where(pd.notnull(df), None)


def get_account_records(user_id: str, repository: AccountsRepository | None = None) -> list[dict]:
    df = get_accounts_df(user_id, repository)
    if df.empty:
        return []

    api_df = df.rename(columns=ACCOUNT_API_COLUMNS)
    api_df = api_df.where(pd.notnull(api_df), None)
    return api_df.to_dict("records")


def create_account(user_id: str, account_code: str, description: str, repository: AccountsRepository | None = None) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    repo.save_account(user_id, account_code, description)
    return {
        "account_code": account_code,
        "description": description,
    }


def update_account_description(
    user_id: str,
    account_code: str,
    description: str,
    repository: AccountsRepository | None = None,
) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    repo.update_account(user_id, account_code, description)
    return {
        "account_code": account_code,
        "description": description,
    }


def remove_account(user_id: str, account_code: str, repository: AccountsRepository | None = None) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    repo.delete_account(user_id, account_code)
    return {
        "account_code": account_code,
        "deleted": True,
    }