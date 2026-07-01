import datetime

import pandas as pd

from backend.app.repositories.holdings_repository import HoldingsRepository


_DEFAULT_REPOSITORY = HoldingsRepository()

HOLDINGS_BASE_COLUMNS = [
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
]

HOLDINGS_ASSET_COLUMNS = [
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

HOLDINGS_API_COLUMNS = {
    "User ID": "user_id",
    "Account Code": "account_code",
    "Holding Date": "holding_date",
    "ISIN": "isin",
    "Quantity": "quantity",
    "Price Currency": "price_currency",
    "Price": "price",
    "Valuation (Price Curr)": "valuation_in_price_currency",
    "FX to EUR": "fx_to_eur",
    "Valuation (EUR)": "valuation_in_eur",
    "Asset Name": "asset_name",
    "Asset Ticker": "asset_ticker",
    "Asset Risk Currency": "asset_risk_currency",
    "Asset Type": "asset_type",
    "Asset Class": "asset_class",
    "Asset Region": "asset_region",
    "Asset Sector": "asset_sector",
    "Asset Industry": "asset_industry",
    "Asset Country": "asset_country",
}


def get_last_selectable_holdings_date(today: datetime.date | None = None) -> datetime.date:
    reference_today = today or datetime.date.today()
    return reference_today - datetime.timedelta(days=1)


def resolve_selected_holdings_date(
    session_value,
    first_date: datetime.date,
    last_date: datetime.date,
) -> datetime.date:
    if not isinstance(session_value, datetime.date):
        return last_date
    if session_value < first_date or session_value > last_date:
        return last_date
    return session_value


def get_holdings_date_range(
    user_id: str,
    today: datetime.date | None = None,
    repository: HoldingsRepository | None = None,
) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    first_date = repo.get_user_holdings_min_date(user_id=user_id)
    last_date = get_last_selectable_holdings_date(today)
    return {
        "user_id": user_id,
        "first_date": first_date,
        "last_date": last_date,
    }


def get_holdings_display_df(
    user_id,
    selected_date,
    repository: HoldingsRepository | None = None,
) -> pd.DataFrame:
    repo = repository or _DEFAULT_REPOSITORY
    raw_holdings = repo.get_daily_holdings(user_id=user_id, holding_date=selected_date)
    if not raw_holdings:
        return pd.DataFrame([], columns=HOLDINGS_BASE_COLUMNS + HOLDINGS_ASSET_COLUMNS)

    holdings_df = pd.DataFrame(raw_holdings)
    relevant_isins = sorted(
        {
            str(value).strip()
            for value in holdings_df.get("isin", pd.Series(dtype=str)).dropna().tolist()
            if str(value).strip()
        }
    )
    asset_rows = repo.get_all_assets_with_labels(relevant_isins)
    asset_df = pd.DataFrame(asset_rows)

    if not asset_df.empty:
        asset_df = asset_df[
            [
                column
                for column in [
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
                ]
                if column in asset_df.columns
            ]
        ].rename(
            columns={
                "Name": "Asset Name",
                "Ticker": "Asset Ticker",
                "Risk Currency": "Asset Risk Currency",
                "Type": "Asset Type",
                "Region": "Asset Region",
                "Sector": "Asset Sector",
                "Industry": "Asset Industry",
                "Country": "Asset Country",
            }
        )

    merged_df = (
        holdings_df.merge(asset_df, left_on="isin", right_on="ISIN", how="left")
        if not asset_df.empty
        else holdings_df.copy()
    )
    if "ISIN" in merged_df.columns:
        merged_df = merged_df.drop(columns=["ISIN"])

    merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()].copy()
    merged_df = merged_df.rename(
        columns={
            "user_id": "User ID",
            "account_code": "Account Code",
            "holding_date": "Holding Date",
            "isin": "ISIN",
            "quantity": "Quantity",
            "price_currency": "Price Currency",
            "price": "Price",
            "valuation_in_price_currency": "Valuation (Price Curr)",
            "exchange_rate_to_eur": "FX to EUR",
            "valuation_in_eur": "Valuation (EUR)",
        }
    )

    preferred_order = HOLDINGS_BASE_COLUMNS + HOLDINGS_ASSET_COLUMNS
    existing_columns = [column for column in preferred_order if column in merged_df.columns]
    merged_df = merged_df[existing_columns]

    if "Holding Date" in merged_df.columns:
        merged_df["Holding Date"] = pd.to_datetime(merged_df["Holding Date"])
        merged_df = merged_df.sort_values(
            by=["Holding Date", "Valuation (EUR)"],
            ascending=[False, False],
        )

    return merged_df


def get_holdings_chart_data(
    filtered_df: pd.DataFrame,
    pie_dimension: str,
    repository: HoldingsRepository | None = None,
):
    repo = repository or _DEFAULT_REPOSITORY
    chart_df = filtered_df.copy()
    if pie_dimension in chart_df.columns:
        chart_df[pie_dimension] = chart_df[pie_dimension].fillna("Unknown").replace("", "Unknown")
    else:
        chart_df[pie_dimension] = "Unknown"

    if "Valuation (EUR)" in chart_df.columns:
        chart_values = pd.to_numeric(chart_df["Valuation (EUR)"], errors="coerce").fillna(0)
    else:
        chart_values = pd.Series([0] * len(chart_df), index=chart_df.index)

    chart_data = (
        pd.DataFrame({pie_dimension: chart_df[pie_dimension], "Valuation (EUR)": chart_values})
        .groupby(pie_dimension, as_index=True)["Valuation (EUR)"]
        .sum()
        .sort_values(ascending=False)
    )

    ref_table_map = {
        "Asset Class": "ref_asset_class",
        "Asset Type": "ref_instrument_type",
        "Asset Region": "ref_region",
        "Asset Sector": "ref_sector",
    }
    ref_table = ref_table_map.get(pie_dimension)
    ref_meta = repo.get_ref_metadata(ref_table) if ref_table else []

    color_by_label = {
        item.get("label"): item.get("color_hex")
        for item in ref_meta
        if item.get("label") and item.get("color_hex")
    }
    order_by_label = {
        item.get("label"): item.get("display_order")
        for item in ref_meta
        if item.get("label")
    }

    if not chart_data.empty:
        chart_data = chart_data.sort_index(
            key=lambda idx: idx.map(lambda label: order_by_label.get(label, 9999))
        )

    return chart_data, color_by_label


def get_holdings_records(
    user_id,
    selected_date,
    repository: HoldingsRepository | None = None,
) -> list[dict]:
    df = get_holdings_display_df(
        user_id=user_id,
        selected_date=selected_date,
        repository=repository,
    )
    if df.empty:
        return []

    api_df = df.rename(columns=HOLDINGS_API_COLUMNS).copy()
    if "holding_date" in api_df.columns:
        api_df["holding_date"] = pd.to_datetime(api_df["holding_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    api_df = api_df.where(pd.notnull(api_df), None)
    return api_df.to_dict("records")


def get_holdings_summary(
    user_id,
    selected_date,
    pie_dimension: str,
    repository: HoldingsRepository | None = None,
) -> dict:
    df = get_holdings_display_df(
        user_id=user_id,
        selected_date=selected_date,
        repository=repository,
    )
    chart_data, color_by_label = get_holdings_chart_data(
        filtered_df=df,
        pie_dimension=pie_dimension,
        repository=repository,
    )

    items = [
        {
            "label": str(label),
            "valuation_eur": float(value),
            "color_hex": color_by_label.get(label),
        }
        for label, value in chart_data.items()
        if float(value) > 0
    ]

    total_valuation_eur = float(sum(item["valuation_eur"] for item in items))
    return {
        "pie_dimension": pie_dimension,
        "total_valuation_eur": total_valuation_eur,
        "items": items,
    }


def get_holdings_reorganization_status(
    user_id: str,
    repository: HoldingsRepository | None = None,
) -> dict | None:
    repo = repository or _DEFAULT_REPOSITORY
    return repo.get_user_holdings_reorganization_status(user_id)


def run_holdings_reorganization(
    user_id: str,
    account_codes: list[str] | None = None,
    dry_run: bool = False,
    repository: HoldingsRepository | None = None,
) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    return repo.reorganize_incremental_holdings(
        user_id=user_id,
        account_codes=account_codes,
        dry_run=dry_run,
    )