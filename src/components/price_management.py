import streamlit as st
import pandas as pd

import src.database as database
from src.utils import apply_advanced_filters



def _build_asset_prices_df():
    raw_data = database.get_asset_prices()
    df = pd.DataFrame(raw_data)
    if df.empty:
        return pd.DataFrame([], columns=["ISIN", "Name", "Price Date", "Price Close", "Price Currency", "Dividend Cash", "Split Factor"])

    if "asset_static_data" in df.columns:
        df["Name"] = df["asset_static_data"].apply(
            lambda x: x.get("name") if isinstance(x, dict) else None
        )
        df["Price Currency"] = df["asset_static_data"].apply(
            lambda x: x.get("price_currency") if isinstance(x, dict) else None
        )
        df = df.drop(columns=["asset_static_data"])

    df = df.rename(columns={
        "isin": "ISIN",
        "price_date": "Price Date",
        "price_close": "Price Close",
        "dividend_cash": "Dividend Cash",
        "split_factor": "Split Factor"
    })
    
    # Reorder columns to desired order
    column_order = ["ISIN", "Name", "Price Date", "Price Close", "Price Currency", "Dividend Cash", "Split Factor"]
    available_cols = [col for col in column_order if col in df.columns]
    return df[available_cols]


def _build_fx_rates_df():
    raw_data = database.get_fx_rates()
    df = pd.DataFrame(raw_data)
    if df.empty:
        return pd.DataFrame([], columns=["Currency", "Date", "Exchange Rate", "Date Original", "Created At", "Updated At"])
    return df.rename(columns={
        "currency": "Currency",
        "rate_date": "Date",
        "exchange_rate": "Exchange Rate",
        "rate_date_original": "Date Original",
        "created_at": "Created At",
        "updated_at": "Updated At"
    })




def price_table_view():
    st.subheader("Asset Prices")
    df = _build_asset_prices_df()
    if df.empty:
        st.info("No asset price records found.")
        return

    filtered_df = apply_advanced_filters(df, "asset_prices")
    st.dataframe(filtered_df, use_container_width=True)


def fx_table_view():
    st.subheader("FX rates")
    st.info("Displayed FX rates are relative to EUR.")
    df = _build_fx_rates_df()
    if df.empty:
        st.info("No FX rate records found.")
        return

    filtered_df = apply_advanced_filters(df, "fx_rates")
    st.dataframe(filtered_df, use_container_width=True)


def price_management_view():
    st.title("Price Data")
    asset_tab, fx_tab = st.tabs(["Asset Prices", "FX rates"])

    with asset_tab:
        price_table_view()

    with fx_tab:
        fx_table_view()




