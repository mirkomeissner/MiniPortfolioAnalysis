import datetime

import streamlit as st
import pandas as pd

import src.database as database
from src.utils import apply_advanced_filters
from src.utils import my_yf
from src.utils import fetch_and_fill_gaps


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




def fetch_and_fill_price_gaps(ticker_symbol, start_date, end_date):
    """
    Core Logic: Fetches data from yfinance and fills calendar gaps (weekends/holidays).
    Returns a list of dictionaries containing 'date', 'value', and 'origin'.
    """
    # Use a 7-day buffer to ensure we have a valid closing price to start with
    fetch_start = start_date - datetime.timedelta(days=7)
    
    ticker = yf.Ticker(ticker_symbol)
    history = ticker.history(
        start=fetch_start.isoformat(),
        end=(end_date + datetime.timedelta(days=1)).isoformat(), # End is exclusive in yf
        interval="1d"
    )
    
    if history is None or history.empty:
        return []

    # Standardize column names (yfinance can be inconsistent)
    history.columns = [c.capitalize() for c in history.columns]
    history.index = history.index.date
    
    results = []
    last_valid_rate = None
    last_valid_origin = None

    # Initialization: Find the most recent price on or before the target start_date
    hist_before = history[history.index <= start_date]
    if not hist_before.empty:
        last_valid_rate = float(hist_before.iloc[-1]["Close"])
        last_valid_origin = hist_before.index[-1]

    # Iterate through every calendar day in the missing range (gap-filling)
    gap_days = pd.date_range(start=start_date, end=end_date, freq='D').date
    for current_day in gap_days:
        # Update price if yfinance provides a real data point for this day
        if current_day in history.index:
            last_valid_rate = float(history.loc[current_day, "Close"])
            last_valid_origin = current_day
        
        # Only append if we have found at least one valid price (handling early history)
        if last_valid_rate is not None:
            results.append({
                "date": current_day,
                "value": last_valid_rate,
                "origin": last_valid_origin
            })
    return results







def _load_missing_fx_rates():
    """
    Orchestrates the FX update process: identifies gaps in DB, calls helper, 
    and saves results. Implements T-1 logic to ensure only EOD prices are saved.
    """
    # 1. Retrieve metadata from database
    # target_starts: dict {currency: start_date_str}
    target_starts_raw = database.get_non_eur_asset_currency_start_dates()
    # current_bounds: dict {currency: {'min': date, 'max': date}}
    current_bounds = database.get_fx_rate_bounds()
    
    if not target_starts_raw:
        st.warning("No non-EUR asset currencies found in database.")
        return

    # T-1 Logic: Only fetch data until yesterday to avoid unstable intraday prices
    today = datetime.date.today()
    limit_date = today - datetime.timedelta(days=1)
    
    all_records = []

    with st.spinner("Updating FX rates..."):
        for currency, target_start_str in target_starts_raw.items():
            currency = currency.upper()
            target_start = pd.to_datetime(target_start_str).date()
            
            # Determine which date ranges are actually missing from the DB
            bounds = current_bounds.get(currency)
            fetch_ranges = []

            if not bounds:
                # Case A: Currency not in DB -> fetch from asset start to yesterday
                if target_start <= limit_date:
                    fetch_ranges.append((target_start, limit_date))
            else:
                # Case B: Check for historical gaps (before existing data)
                if target_start < bounds['min']:
                    fetch_ranges.append((target_start, bounds['min'] - datetime.timedelta(days=1)))
                
                # Case C: Check for freshness gaps (after existing data)
                if bounds['max'] < limit_date:
                    fetch_ranges.append((bounds['max'] + datetime.timedelta(days=1), limit_date))

            # 2. Process identified gaps using the generic helper
            for start, end in fetch_ranges:
                symbol = f"EUR{currency}=X"
                gap_data = fetch_and_fill_price_gaps(symbol, start, end)
                
                # Map generic results to the specific FX table schema
                for entry in gap_data:
                    all_records.append({
                        "currency": currency,
                        "rate_date": entry["date"].isoformat(),
                        "exchange_rate": entry["value"],
                        "rate_date_origin": entry["origin"].isoformat()
                    })

    # 3. Bulk save to database
    if all_records:
        try:
            database.save_fx_rates_bulk(all_records)
            st.success(f"Successfully processed {len(all_records)} FX records.")
        except Exception as e:
            st.error(f"Failed to save records to database: {e}")
    else:
        st.info("Everything is up to date (End-of-Day).")




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




