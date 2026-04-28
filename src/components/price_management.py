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
    """
    Lädt fehlende FX-Kurse von yfinance und füllt Lücken (Wochenenden) auf.
    Sichert durch T-1 Logik ab, dass nur finale Schlusskurse gespeichert werden.
    """
    # 1. Gewünschte Startdaten laut Assets (Strings aus DB)
    target_starts_raw = database.get_non_eur_asset_currency_start_dates()
    
    # 2. Vorhandene Datenbereiche in der DB (bereits date-Objekte)
    current_bounds = database.get_fx_rate_bounds()
    
    if not target_starts_raw:
        st.warning("Keine Währungen (außer EUR) mit Startdatum gefunden.")
        return

    # T-1 LOGIK: Wir laden nur bis GESTERN, um keine Intraday-Kurse zu speichern
    today = datetime.date.today()
    limit_date = today - datetime.timedelta(days=1)
    
    all_records = []

    with st.spinner("Prüfe FX-Lücken und lade Daten von yfinance..."):
        for currency, target_start_str in target_starts_raw.items():
            currency = currency.upper()
            
            # Konvertierung String -> Date-Objekt für Berechnungen
            target_start = pd.to_datetime(target_start_str).date()
            
            bounds = current_bounds.get(currency)
            fetch_ranges = []

            if not bounds:
                # Fall A: Währung komplett neu -> Start bis gestern
                if target_start <= limit_date:
                    fetch_ranges.append((target_start, limit_date))
            else:
                db_min = bounds['min']
                db_max = bounds['max']

                # Fall B: Historische Lücke (Asset startet vor DB-Einträgen)
                if target_start < db_min:
                    fetch_ranges.append((target_start, db_min - datetime.timedelta(days=1)))
                
                # Fall C: Aktualitäts-Lücke (DB endet vor gestern)
                if db_max < limit_date:
                    fetch_ranges.append((db_max + datetime.timedelta(days=1), limit_date))

            # --- Datenabruf für die berechneten Lücken ---
            for start, end in fetch_ranges:
                symbol = f"EUR{currency}=X"
                
                # 7-Tage-Puffer für die Lückenfüller-Initialisierung
                fetch_start = start - datetime.timedelta(days=7)
                
                try:
                    ticker = my_yf.Ticker(symbol)
                    history = ticker.history(
                        start=fetch_start.isoformat(),
                        end=(end + datetime.timedelta(days=1)).isoformat(), # +1 weil exklusiv
                        interval="1d"
                    )
                    
                    if history is None or history.empty:
                        continue

                    # Normalisierung der yfinance-Daten
                    history.columns = [c.capitalize() for c in history.columns]
                    history.index = history.index.date
                    
                    last_valid_rate = None
                    last_valid_origin = None

                    # Initialisierung des "letzten Kurses" vor dem Lücken-Beginn
                    hist_before = history[history.index <= start]
                    if not hist_before.empty:
                        last_valid_rate = float(hist_before.iloc[-1]["Close"])
                        last_valid_origin = historical_before.index[-1]

                    # Loop über jeden Kalendertag der Lücke (Gap-Filling)
                    gap_days = pd.date_range(start=start, end=end, freq='D').date
                    for current_day in gap_days:
                        # Haben wir einen echten Kurs für diesen Tag?
                        if current_day in history.index:
                            last_valid_rate = float(history.loc[current_day, "Close"])
                            last_valid_origin = current_day
                        
                        # Nur hinzufügen, wenn wir einen Basiswert gefunden haben
                        if last_valid_rate is not None:
                            all_records.append({
                                "currency": currency,
                                "rate_date": current_day.isoformat(),
                                "exchange_rate": last_valid_rate,
                                "rate_date_origin": last_valid_origin.isoformat()
                            })
                            
                except Exception as e:
                    st.error(f"Fehler bei {symbol} ({start} bis {end}): {e}")

    # 3. Bulk-Save in die Datenbank
    if all_records:
        database.save_fx_rates_bulk(all_records)
        st.success(f"{len(all_records)} FX-Datensätze erfolgreich aktualisiert.")
    else:
        st.info("Alle Kurse sind bereits auf dem Stand von gestern (End-of-Day).")


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




