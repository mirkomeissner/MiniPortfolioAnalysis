import datetime

import streamlit as st
import pandas as pd

import src.database as database
from src.utils.ui_components import apply_advanced_filters
from src.utils.yf_wrapper import my_yf


def _build_asset_prices_df():
    raw_data = database.get_asset_prices()
    df = pd.DataFrame(raw_data)
    if df.empty:
        return pd.DataFrame([], columns=["ISIN", "Name", "Price Date", "Price Close"])

    if "asset_static_data" in df.columns:
        df["Name"] = df["asset_static_data"].apply(
            lambda x: x.get("name") if isinstance(x, dict) else None
        )
        df = df.drop(columns=["asset_static_data"])

    return df.rename(columns={
        "isin": "ISIN",
        "price_date": "Price Date",
        "price_close": "Price Close"
    })


def _build_fx_rates_df():
    raw_data = database.get_fx_rates()
    df = pd.DataFrame(raw_data)
    if df.empty:
        return pd.DataFrame([], columns=["Currency", "Date", "Exchange Rate"])
    return df.rename(columns={
        "currency": "Currency",
        "rate_date": "Date",
        "exchange_rate": "Exchange Rate"
    })



def _reload_all_fx_rates():
    currency_start_dates = database.get_non_eur_asset_currency_start_dates()
    if not currency_start_dates:
        st.warning("No non-EUR currencies with a price start date were found.")
        return

    today = datetime.date.today()
    records = []
    
    with st.spinner("Reloading FX rates from yfinance..."):
        for currency, start_date in currency_start_dates.items():
            if not currency or currency.strip().upper() == "EUR":
                continue

            currency = currency.upper()
            symbol = f"EUR{currency}=X"
            
            try:
                ticker = my_yf.Ticker(symbol)
                history = ticker.history(
                    start=start_date,
                    end=(today + datetime.timedelta(days=1)).isoformat(),
                    interval="1d"
                )
            except Exception as e:
                st.error(f"Failed to fetch {symbol}: {e}")
                continue

            if history is None or history.empty:
                st.info(f"No FX history available for {symbol}.")
                continue

            # Spaltennamen normalisieren
            history.columns = [c.capitalize() for c in history.columns]
            if "Close" not in history.columns:
                continue

            # --- Lückenfüller Logik ---
            
            # Wir erstellen einen Datumsbereich vom Startdatum bis heute
            all_days = pd.date_range(start=start_date, end=today, freq='D').date
            
            # Wir mappen die vorhandenen yfinance-Daten (Index ist DatetimeIndex)
            # Wir konvertieren den Index zu .date(), um den Vergleich zu vereinfachen
            history.index = history.index.date
            
            last_valid_rate = None
            last_valid_origin = None

            for current_day in all_days:
                if current_day in history.index:
                    # Wir haben einen echten Kurs von yfinance
                    last_valid_rate = float(history.loc[current_day, "Close"])
                    last_valid_origin = current_day
                
                # Wenn wir bereits mindestens einen Kurs gesehen haben, füllen wir ab da auf
                if last_valid_rate is not None:
                    records.append({
                        "currency": currency,
                        "rate_date": current_day.isoformat(),
                        "exchange_rate": last_valid_rate,
                        "rate_date_origin": last_valid_origin.isoformat()
                    })

    if records:
        database.save_fx_rates_bulk(records)
        st.success(f"Reloaded FX rates and filled gaps for {len(currency_start_dates)} currencies.")
    else:
        st.info("No FX rate records were updated.")


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
        is_admin = st.session_state.get("is_admin", False)
        if st.button("Reload all FX rates", disabled=not is_admin, use_container_width=True):
            _reload_all_fx_rates()

        if not is_admin:
            st.info("Only admin users can reload FX rates.")

        fx_table_view()




