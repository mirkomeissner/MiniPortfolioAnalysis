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



def _load_missing_fx_rates():
    # 1. Gewünschte Startdaten laut Assets
    target_starts = database.get_non_eur_asset_currency_start_dates()
    # 2. Vorhandene Daten in der DB
    current_bounds = database.get_fx_rate_bounds()
    
    if not target_starts:
        st.warning("No non-EUR currencies found.")
        return

    today = datetime.date.today()
    all_records = []

    with st.spinner("Checking for missing FX rates..."):
        for currency, target_start in target_starts.items():
            currency = currency.upper()
            bounds = current_bounds.get(currency)
            
            fetch_ranges = []

            if not bounds:
                # Fall A: Währung gar nicht in DB -> Komplett laden
                fetch_ranges.append((target_start, today))
            else:
                db_min = bounds['min']
                db_max = bounds['max']

                # Fall B: Historische Lücke (Asset-Start ist früher als DB-Bestand)
                if target_start < db_min:
                    fetch_ranges.append((target_start, db_min - datetime.timedelta(days=1)))
                
                # Fall C: Aktualitäts-Lücke (DB-Stand ist älter als heute)
                if db_max < today:
                    fetch_ranges.append((db_max + datetime.timedelta(days=1), today))

            # --- Daten abrufen pro identifizierter Lücke ---
            for start, end in fetch_ranges:
                symbol = f"EUR{currency}=X"
                # Puffer für Gap-Filling (7 Tage zurück)
                fetch_start = start - datetime.timedelta(days=7)
                
                try:
                    ticker = my_yf.Ticker(symbol)
                    history = ticker.history(
                        start=fetch_start.isoformat(),
                        end=(end + datetime.timedelta(days=1)).isoformat(),
                        interval="1d"
                    )
                    
                    if history is None or history.empty:
                        continue

                    history.columns = [c.capitalize() for c in history.columns]
                    history.index = history.index.date
                    
                    # Lückenfüller Logik innerhalb des Fensters
                    last_valid_rate = None
                    last_valid_origin = None

                    # Initialisierung mit Puffer
                    hist_before = history[history.index <= start]
                    if not hist_before.empty:
                        last_valid_rate = float(hist_before.iloc[-1]["Close"])
                        last_valid_origin = hist_before.index[-1]

                    # Loop nur über die spezifische Lücke
                    gap_days = pd.date_range(start=start, end=end, freq='D').date
                    for current_day in gap_days:
                        if current_day in history.index:
                            last_valid_rate = float(history.loc[current_day, "Close"])
                            last_valid_origin = current_day
                        
                        if last_valid_rate is not None:
                            all_records.append({
                                "currency": currency,
                                "rate_date": current_day.isoformat(),
                                "exchange_rate": last_valid_rate,
                                "rate_date_origin": last_valid_origin.isoformat()
                            })
                except Exception as e:
                    st.error(f"Error updating {currency} from {start} to {end}: {e}")

    # 3. Speichern
    if all_records:
        database.save_fx_rates_bulk(all_records)
        st.success(f"Added {len(all_records)} missing FX rate entries.")
    else:
        st.info("Everything up to date. No requests sent to yfinance.")


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
        if st.button("Load missing FX rates", disabled=not is_admin, use_container_width=True):
            _load_missing_fx_rates()

        if not is_admin:
            st.info("Only admin users can load FX rates.")

        fx_table_view()




