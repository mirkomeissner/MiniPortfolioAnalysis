import pandas as pd

from backend.app.repositories.assets_repository import AssetsRepository


ASSET_DISPLAY_COLUMNS = [
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

ASSET_API_COLUMNS = {
    "ISIN": "isin",
    "Name": "name",
    "Ticker": "ticker",
    "Risk Currency": "risk_currency",
    "Type": "instrument_type",
    "Asset Class": "asset_class",
    "Region": "region",
    "Sector": "sector",
    "Industry": "industry",
    "Country": "country",
    "Price Source": "price_source",
    "Price Currency": "price_currency",
    "Price Start Date": "price_start_date",
    "Closed On": "closed_on",
    "Created At": "created_at",
    "Created By": "created_by",
    "Updated At": "updated_at",
    "Updated By": "updated_by",
}

_DEFAULT_REPOSITORY = AssetsRepository()


def search_exchange_ticker_records(
    isin: str | None = None,
    name: str | None = None,
    active_only: bool = True,
    repository: AssetsRepository | None = None,
) -> list[dict]:
    repo = repository or _DEFAULT_REPOSITORY
    return repo.search_exchange_tickers(isin=isin, name=name, active_only=active_only)


def get_assets_df(isins: list[str] | None = None, repository: AssetsRepository | None = None) -> pd.DataFrame:
    repo = repository or _DEFAULT_REPOSITORY
    return build_assets_df(repo.get_all_assets_with_labels(isins))


def build_assets_df(raw_data) -> pd.DataFrame:
    df = pd.DataFrame(raw_data)
    if df.empty:
        return pd.DataFrame([], columns=ASSET_DISPLAY_COLUMNS)

    available_columns = [column for column in ASSET_DISPLAY_COLUMNS if column in df.columns]
    df = df[available_columns]
    return df.astype(object).where(pd.notnull(df), None)


def get_asset_records(isins: list[str] | None = None, repository: AssetsRepository | None = None) -> list[dict]:
    df = get_assets_df(isins=isins, repository=repository)
    if df.empty:
        return []

    api_df = df.rename(columns=ASSET_API_COLUMNS)
    api_df = api_df.where(pd.notnull(api_df), None)
    return api_df.to_dict("records")


def create_asset(asset_data: dict, repository: AssetsRepository | None = None) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    repo.save_asset_static_data(asset_data)
    return asset_data


def update_asset(isin: str, update_data: dict, repository: AssetsRepository | None = None) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    repo.update_asset_static_data(isin, update_data)
    return {"isin": isin, **update_data}