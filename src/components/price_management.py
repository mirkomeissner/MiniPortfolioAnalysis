import datetime

import streamlit as st
import pandas as pd

import src.database as database
from src.utils import apply_advanced_filters
from src.utils import my_yf



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
        return pd.DataFrame([], columns=["Currency", "Date", "Exchange Rate", "Date Original", "Created At", "Updated At"])
    return df.rename(columns={
        "currency": "Currency",
        "rate_date": "Date",
        "exchange_rate": "Exchange Rate",
        "rate_date_original": "Date Original",
        "created_at": "Created At",
        "updated_at": "Updated At"
    })




def fetch_and_fill_price_gaps(symbol, start_date, end_date, source_df):
    """
    Core Logic: Processes data from a pre-fetched DataFrame and fills calendar gaps.
    'source_df' must be a DataFrame containing at least a 'Close' column.
    """
    if source_df is None or source_df.empty:
        return []

    # Standardize index and columns
    df = source_df.copy()
    df.columns = [c.capitalize() for c in df.columns]
    df.index = pd.to_datetime(df.index).date
    
    results = []
    last_valid_rate = None
    last_valid_origin = None

    # Initialization: Find the most recent price on or before the target start_date
    hist_before = df[df.index <= start_date]
    if not hist_before.empty:
        last_valid_rate = float(hist_before.iloc[-1]["Close"])
        last_valid_origin = hist_before.index[-1]

    # Iterate through every calendar day (Gap-Filling)
    gap_days = pd.date_range(start=start_date, end=end_date, freq='D').date
    for current_day in gap_days:
        if current_day in df.index:
            last_valid_rate = float(df.loc[current_day, "Close"])
            last_valid_origin = current_day
        
        if last_valid_rate is not None:
            results.append({
                "date": current_day,
                "value": last_valid_rate,
                "origin": last_valid_origin
            })
    return results

def _load_missing_fx_rates():
    """
    Orchestrates the FX update process with special handling for GBX (Pence Sterling).
    Fetches EURGBP=X for GBX and multiplies by 100.
    """
    target_starts_raw = database.get_non_eur_asset_currency_start_dates()
    current_bounds = database.get_fx_rate_bounds()
    
    if not target_starts_raw:
        st.warning("No non-EUR asset currencies found.")
        return

    today = datetime.date.today()
    limit_date = today - datetime.timedelta(days=1)
    
    # 1. Identify all required symbols and handle GBX mapping
    currencies = [c.upper() for c in target_starts_raw.keys()]
    
    # Mapping for special currencies that don't have their own Yahoo FX pair
    # GBX (Pence) -> use GBP (Pound)
    fx_mapping = {
        "GBX": "GBP"
    }

    # Build unique symbols list for download
    symbols = []
    for c in currencies:
        base_curr = fx_mapping.get(c, c)
        symbol = f"EUR{base_curr}=X"
        if symbol not in symbols:
            symbols.append(symbol)
    
    # Find global minimum start to fetch everything in one bulk request
    global_min_start = min([pd.to_datetime(d).date() for d in target_starts_raw.values()])
    fetch_start = global_min_start - datetime.timedelta(days=7)

    all_records = []

    with st.spinner("Downloading FX data bundle..."):
        bundle_df = my_yf.download(
            symbols,
            start=fetch_start.isoformat(),
            end=(limit_date + datetime.timedelta(days=1)).isoformat(),
            group_by='ticker',
            threads=True
        )

    # 2. Process each currency locally
    for currency in currencies:
        # Determine which symbol to look for in the downloaded bundle
        base_curr = fx_mapping.get(currency, currency)
        symbol = f"EUR{base_curr}=X"
        
        target_start = pd.to_datetime(target_starts_raw[currency]).date()
        
        # Extract history from bundle
        if len(symbols) > 1:
            if symbol not in bundle_df:
                continue
            history = bundle_df[symbol].dropna(subset=["Close"])
        else:
            history = bundle_df.dropna(subset=["Close"])

        bounds = current_bounds.get(currency)
        fetch_ranges = []

        # Determine gaps
        if not bounds:
            if target_start <= limit_date:
                fetch_ranges.append((target_start, limit_date))
        else:
            if target_start < bounds['min']:
                fetch_ranges.append((target_start, bounds['min'] - datetime.timedelta(days=1)))
            if bounds['max'] < limit_date:
                fetch_ranges.append((bounds['max'] + datetime.timedelta(days=1), limit_date))

        # Fill gaps from the already downloaded 'history'
        for start, end in fetch_ranges:
            gap_data = fetch_and_fill_price_gaps(symbol, start, end, history)
            for entry in gap_data:
                # Apply conversion factor if necessary (e.g., GBP -> GBX)
                final_rate = entry["value"]
                if currency == "GBX":
                    final_rate = final_rate * 100
                
                all_records.append({
                    "currency": currency,
                    "rate_date": entry["date"].isoformat(),
                    "exchange_rate": final_rate,
                    "rate_date_origin": entry["origin"].isoformat()
                })

    # 3. Save to DB
    if all_records:
        try:
            database.save_fx_rates_bulk(all_records)
            st.success(f"Successfully updated {len(all_records)} records.")
        except Exception as e:
            st.error(f"DB Error: {e}")
    else:
        st.info("Everything is up to date.")




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




