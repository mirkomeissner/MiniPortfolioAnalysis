import pandas as pd

from backend.app.repositories.prices_repository import PricesRepository


EMPTY_ASSET_PRICES_DF = pd.DataFrame(
    [],
    columns=[
        "ISIN",
        "Name",
        "Price Date",
        "Price Close",
        "Price Currency",
        "Dividend Cash",
        "Split Factor",
    ],
)

EMPTY_FX_RATES_DF = pd.DataFrame(
    [],
    columns=[
        "Currency",
        "Date",
        "Exchange Rate",
        "Date Original",
        "Created At",
        "Updated At",
    ],
)

ASSET_PRICE_API_COLUMNS = {
    "ISIN": "isin",
    "Name": "name",
    "Price Date": "price_date",
    "Price Close": "price_close",
    "Price Currency": "price_currency",
    "Dividend Cash": "dividend_cash",
    "Split Factor": "split_factor",
}

FX_RATE_API_COLUMNS = {
    "Currency": "currency",
    "Date": "date",
    "Exchange Rate": "exchange_rate",
    "Date Original": "date_original",
    "Created At": "created_at",
    "Updated At": "updated_at",
}

_DEFAULT_REPOSITORY = PricesRepository()


def get_asset_prices_df(repository: PricesRepository | None = None) -> pd.DataFrame:
    repo = repository or _DEFAULT_REPOSITORY
    return build_asset_prices_df(repo.get_asset_prices())


def build_asset_prices_df(raw_data) -> pd.DataFrame:
    df = pd.DataFrame(raw_data)
    if df.empty:
        return EMPTY_ASSET_PRICES_DF.copy()

    if "asset_static_data" in df.columns:
        df["Name"] = df["asset_static_data"].apply(
            lambda value: value.get("name") if isinstance(value, dict) else None
        )
        df["Price Currency"] = df["asset_static_data"].apply(
            lambda value: value.get("price_currency") if isinstance(value, dict) else None
        )
        df = df.drop(columns=["asset_static_data"])

    df = df.rename(
        columns={
            "isin": "ISIN",
            "price_date": "Price Date",
            "price_close": "Price Close",
            "dividend_cash": "Dividend Cash",
            "split_factor": "Split Factor",
        }
    )

    column_order = [
        "ISIN",
        "Name",
        "Price Date",
        "Price Close",
        "Price Currency",
        "Dividend Cash",
        "Split Factor",
    ]
    available_columns = [column for column in column_order if column in df.columns]
    return df[available_columns]


def get_asset_price_records(repository: PricesRepository | None = None) -> list[dict]:
    df = get_asset_prices_df(repository)
    if df.empty:
        return []

    api_df = df.rename(columns=ASSET_PRICE_API_COLUMNS)
    api_df = api_df.where(pd.notnull(api_df), None)
    return api_df.to_dict("records")


def get_fx_rates_df(repository: PricesRepository | None = None) -> pd.DataFrame:
    repo = repository or _DEFAULT_REPOSITORY
    return build_fx_rates_df(repo.get_fx_rates())


def build_fx_rates_df(raw_data) -> pd.DataFrame:
    df = pd.DataFrame(raw_data)
    if df.empty:
        return EMPTY_FX_RATES_DF.copy()

    return df.rename(
        columns={
            "currency": "Currency",
            "rate_date": "Date",
            "exchange_rate": "Exchange Rate",
            "rate_date_original": "Date Original",
            "created_at": "Created At",
            "updated_at": "Updated At",
        }
    )


def get_fx_rate_records(repository: PricesRepository | None = None) -> list[dict]:
    df = get_fx_rates_df(repository)
    if df.empty:
        return []

    api_df = df.rename(columns=FX_RATE_API_COLUMNS)
    api_df = api_df.where(pd.notnull(api_df), None)
    return api_df.to_dict("records")