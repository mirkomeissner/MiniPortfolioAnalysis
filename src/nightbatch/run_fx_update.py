import os
import sys
import datetime
import pandas as pd

# -------------------------------------------------------------------------
# PATH SETUP
# -------------------------------------------------------------------------
# Get the directory of the current script (nightbatch/)
script_dir = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (one level up)
project_root = os.path.abspath(os.path.join(script_dir, os.pardir))
# Append project root to sys.path so Python can find 'src' and 'components'
sys.path.append(project_root)

# -------------------------------------------------------------------------
# ENVIRONMENT & STREAMLIT EMULATION
# -------------------------------------------------------------------------
import os
import streamlit as st

# 1. Versuche, die Secrets aus den GitHub Umgebungsvariablen zu laden
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

# 2. Wenn wir bei GitHub Actions sind, füttern wir Streamlits internes Dictionary
if supabase_url and supabase_key:
    # Wir umgehen den Schreibschutz, indem wir direkt das interne _secrets-Dict befüllen
    if st.secrets._secrets is None:
        st.secrets._secrets = {}
    st.secrets._secrets["SUPABASE_URL"] = supabase_url
    st.secrets._secrets["SUPABASE_SERVICE_KEY"] = supabase_key
else:
    # 3. Wenn wir lokal im Codespace sind, prüfen wir ganz normal st.secrets
    if "SUPABASE_URL" not in st.secrets or "SUPABASE_SERVICE_KEY" not in st.secrets:
        raise ValueError("Weder GitHub-Umgebungsvariablen noch st.secrets (.toml) gefunden!")




# Now it's safe to import internal modules
import src.database as database
from src.utils import my_yf
from src.components import fetch_and_fill_price_gaps


def headless_load_missing_fx_rates():
    """
    Orchestrates an API-efficient FX update process.
    - Uses a 7-day window for normal incremental daily updates.
    - Automatically falls back to full history mode if a currency is new 
      or has a large database gap (> 7 days).
    """
    print("Starting API-optimized automated FX rates update...")

    # Fetch required start dates from assets and existing bounds from DB
    target_starts_raw = database.get_non_eur_asset_currency_start_dates()
    current_bounds = database.get_fx_rate_bounds()

    if not target_starts_raw:
        print("No non-EUR asset currencies found in the database.")
        return

    # Calculate date thresholds
    today = datetime.date.today()
    limit_date = today - datetime.timedelta(days=1) # Yesterday (EOD)
    currencies = [c.upper() for c in target_starts_raw.keys()]
    
    # Mapping for special currencies that don't have a direct Yahoo FX pair
    fx_mapping = {"GBX": "GBP"}

    # Define lists for the two different data fetching strategies
    incremental_symbols = []
    historical_requests = [] # List of tuples: (symbol, fetch_start_date)

    # -------------------------------------------------------------------------
    # STRATEGY ROUTING WEICHE
    # -------------------------------------------------------------------------
    for currency in currencies:
        base_curr = fx_mapping.get(currency, currency)
        symbol = f"EUR{base_curr}=X"
        target_start = pd.to_datetime(target_starts_raw[currency]).date()
        bounds = current_bounds.get(currency)

        if not bounds:
            # Case 1: Brand new currency, no records in DB -> Fetch full history
            print(f"[{currency}] Routed to HISTORY: Brand new currency.")
            historical_requests.append((symbol, target_start - datetime.timedelta(days=7)))
            
        elif target_start < bounds['min']:
            # Case 2: Historical hole at the beginning -> Fetch full history
            print(f"[{currency}] Routed to HISTORY: Target start date is older than DB min date.")
            historical_requests.append((symbol, target_start - datetime.timedelta(days=7)))
            
        elif bounds['max'] < limit_date and (limit_date - bounds['max']).days > 7:
            # Case 3: Large data gap found (> 7 days). Cannot use incremental mode
            # because the 7-day payload won't cover the entire missing period.
            print(f"[{currency}] Routed to HISTORY: Large gap detected ({ (limit_date - bounds['max']).days } days).")
            historical_requests.append((symbol, bounds['max'] - datetime.timedelta(days=7)))
            
        else:
            # Case 4: Normal daily operations (Gap <= 7 days) -> Use efficient incremental mode
            if symbol not in incremental_symbols:
                incremental_symbols.append(symbol)

    all_records = []

    # -------------------------------------------------------------------------
    # STRATEGY 1: INCREMENTAL MODE (API-Efficient Normal Operation)
    # -------------------------------------------------------------------------
    if incremental_symbols:
        short_fetch_start = today - datetime.timedelta(days=7)
        print(f"[API INCREMENTAL] Fetching last 7 days only for: {incremental_symbols}")
        
        bundle_df = my_yf.download(
            incremental_symbols,
            start=short_fetch_start.isoformat(),
            end=(limit_date + datetime.timedelta(days=1)).isoformat(),
            group_by='ticker',
            threads=True
        )
        
        for currency in currencies:
            base_curr = fx_mapping.get(currency, currency)
            symbol = f"EUR{base_curr}=X"
            if symbol not in incremental_symbols:
                continue
                
            bounds = current_bounds.get(currency)
            if bounds and bounds['max'] < limit_date:
                start_gap = bounds['max'] + datetime.timedelta(days=1)
                
                # Handle multi-ticker vs single-ticker DataFrame structures from yfinance
                if len(incremental_symbols) > 1:
                    history = bundle_df[symbol].dropna(subset=["Close"]) if symbol in bundle_df else pd.DataFrame()
                else:
                    history = bundle_df.dropna(subset=["Close"])

                # Calculate gaps and extract only the single missing day(s) from the 7-day pool
                gap_data = fetch_and_fill_price_gaps(symbol, start_gap, limit_date, history)
                for entry in gap_data:
                    final_rate = entry["value"] * 100 if currency == "GBX" else entry["value"]
                    all_records.append({
                        "currency": currency,
                        "rate_date": entry["date"].isoformat(),
                        "exchange_rate": final_rate,
                        "rate_date_original": entry["origin"].isoformat()
                    })

    # -------------------------------------------------------------------------
    # STRATEGY 2: HISTORICAL MODE (Fallback Sonderfall)
    # -------------------------------------------------------------------------
    if historical_requests:
        print(f"[API HISTORICAL] Executing full history downloads for: {historical_requests}")
        for symbol, f_start in historical_requests:
            # Dedicated API call for the specific historical request
            hist_df = my_yf.download(
                symbol,
                start=f_start.isoformat(),
                end=(limit_date + datetime.timedelta(days=1)).isoformat(),
                threads=False
            )
            
            # Match downloaded data back to corresponding database currency rows
            for currency in currencies:
                if f"EUR{fx_mapping.get(currency, currency)}=X" != symbol:
                    continue
                
                target_start = pd.to_datetime(target_starts_raw[currency]).date()
                bounds = current_bounds.get(currency)
                fetch_ranges = []

                if not bounds:
                    fetch_ranges.append((target_start, limit_date))
                else:
                    if target_start < bounds['min']:
                        fetch_ranges.append((target_start, bounds['min'] - datetime.timedelta(days=1)))
                    if bounds['max'] < limit_date:
                        fetch_ranges.append((bounds['max'] + datetime.timedelta(days=1), limit_date))

                history = hist_df.dropna(subset=["Close"])
                for start, end in fetch_ranges:
                    gap_data = fetch_and_fill_price_gaps(symbol, start, end, history)
                    for entry in gap_data:
                        final_rate = entry["value"] * 100 if currency == "GBX" else entry["value"]
                        all_records.append({
                            "currency": currency,
                            "rate_date": entry["date"].isoformat(),
                            "exchange_rate": final_rate,
                            "rate_date_original": entry["origin"].isoformat()
                        })

    # -------------------------------------------------------------------------
    # DATABASE PERSISTENCE
    # -------------------------------------------------------------------------
    if all_records:
        try:
            # Uses the admin service-role client internally to bypass RLS
            database.save_fx_rates_bulk(all_records)
            print(f"Successfully upserted {len(all_records)} FX records into Supabase.")
        except Exception as e:
            print(f"Database Error while saving records: {e}")
            sys.exit(1)
    else:
        print("Everything is up to date. No new records to insert.")


if __name__ == "__main__":
    headless_load_missing_fx_rates()

