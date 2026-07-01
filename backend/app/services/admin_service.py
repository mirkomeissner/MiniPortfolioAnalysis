import pandas as pd

from backend.app.repositories.admin_repository import AdminRepository


ADMIN_DISPLAY_COLUMNS = [
    "ID",
    "Username",
    "Email",
    "Is Approved",
    "Created At",
    "Email Confirmed At",
]

ADMIN_API_COLUMNS = {
    "ID": "id",
    "Username": "username",
    "Email": "email",
    "Is Approved": "is_approved",
    "Created At": "created_at",
    "Email Confirmed At": "email_confirmed_at",
}

_DEFAULT_REPOSITORY = AdminRepository()


def get_admin_users_df(repository: AdminRepository | None = None) -> pd.DataFrame:
    repo = repository or _DEFAULT_REPOSITORY
    return build_admin_users_df(repo.get_all_users())


def build_admin_users_df(raw_data) -> pd.DataFrame:
    df = pd.DataFrame(raw_data)
    if df.empty:
        return pd.DataFrame([], columns=ADMIN_DISPLAY_COLUMNS)

    df = df.rename(
        columns={
            "id": "ID",
            "username": "Username",
            "email": "Email",
            "is_approved": "Is Approved",
            "created_at": "Created At",
            "email_confirmed_at": "Email Confirmed At",
        }
    )
    available_columns = [column for column in ADMIN_DISPLAY_COLUMNS if column in df.columns]
    return df[available_columns]


def get_admin_user_records(repository: AdminRepository | None = None) -> list[dict]:
    df = get_admin_users_df(repository)
    if df.empty:
        return []

    api_df = df.rename(columns=ADMIN_API_COLUMNS)
    api_df = api_df.where(pd.notnull(api_df), None)
    return api_df.to_dict("records")


def set_user_approval(user_id: str, is_approved: bool, repository: AdminRepository | None = None) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    repo.update_user_approval(user_id, is_approved)
    return {
        "user_id": user_id,
        "is_approved": is_approved,
        "updated": True,
    }