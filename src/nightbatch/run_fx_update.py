import os
import sys
import datetime
import pandas as pd

# 1. PATH SETUP (MUSS ganz nach oben!)
# -------------------------------------------------------------------------
# Verzeichnis des aktuellen Skripts (src/nightbatch/)
script_dir = os.path.dirname(os.path.abspath(__file__))
# Das Projekt-Hauptverzeichnis liegt ZWEI Ebenen höher (wegen src/nightbatch)
project_root = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))

# Falls project_root noch nicht im Suchpfad ist, fügen wir es ganz vorne hinzu
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# 2. ENVIRONMENT & STREAMLIT EMULATION
# -------------------------------------------------------------------------
import os
import streamlit as st

# Wir laden alle drei Variablen sauber und getrennt aus der GitHub-Umgebung
supabase_url = os.environ.get("SUPABASE_URL")
supabase_service_key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase_key = os.environ.get("SUPABASE_KEY")

if supabase_url and supabase_service_key and supabase_key:
    if st.secrets._secrets is None:
        st.secrets._secrets = {}
        
    # Jeder Key landet genau da, wo er hingehört. Keine Kopien, keine Täuschung.
    st.secrets._secrets["SUPABASE_URL"] = supabase_url
    st.secrets._secrets["SUPABASE_SERVICE_KEY"] = supabase_service_key
    st.secrets._secrets["SUPABASE_KEY"] = supabase_key
else:
    if "SUPABASE_URL" not in st.secrets or "SUPABASE_SERVICE_KEY" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
        raise ValueError("Es fehlen benötigte Keys in den Umgebungsvariablen oder der secrets.toml!")




# 3. INTERNE MODULE IMPORTIEREN (Jetzt weiß Python, wo 'src' liegt)
# -------------------------------------------------------------------------



# Now it's safe to import internal modules
import src.database as database
from src.utils import my_yf, fetch_and_fill_price_gaps


def _normalize_fx_rate_value(value):
    try:
        return float(value)
    except Exception:
        return None


def _normalize_fx_rate_date(value):
    try:
        return pd.to_datetime(value).date().isoformat()
    except Exception:
        return None


def headless_load_missing_fx_rates():
    """
    Orchestrates an API-efficient FX update process.
    - Uses a 7-day window for normal incremental daily updates.
    - Automatically falls back to full history mode if a currency is new 
      or has a large database gap (> 7 days).
    """
    print("Starting API-optimized automated FX rates update...")

    # Fetch required start dates from assets and existing bounds from DB
    target_starts_raw = database.get_non_eur_asset_currency_start_dates(use_admin=True)
    current_bounds = database.get_fx_rate_bounds(use_admin=True)

    if not target_starts_raw:
        print("No non-EUR asset currencies found in the database.")
        return

    today = datetime.date.today()
    limit_date = today - datetime.timedelta(days=1)
    fx_mapping = {"GBX": "GBP"}

    request_plan = []
    for currency, start_date in target_starts_raw.items():
        currency = currency.upper()
        fx_start = pd.to_datetime(start_date).date()
        bounds = current_bounds.get(currency)

        if not bounds or fx_start < bounds["min"]:
            request_start = fx_start - datetime.timedelta(days=7)
        else:
            request_start = bounds["max"] - datetime.timedelta(days=35)

        request_plan.append((currency, fx_start, request_start))

    all_records = []

    # -------------------------------------------------------------------------
    # NIGHTBATCH FX LOAD
    # -------------------------------------------------------------------------
    for currency, fx_start, request_start in request_plan:
        base_currency = fx_mapping.get(currency, currency)
        symbol = f"EUR{base_currency}=X"
        bounds = current_bounds.get(currency) or {}
        bound_min = bounds.get("min") if bounds else None
        bound_max = bounds.get("max") if bounds else None
        print(f"[{currency}] symbol={symbol} fx_start={fx_start.isoformat()} bounds[min]={bound_min} bounds[max]={bound_max} request_start={request_start.isoformat()} limit_date={limit_date.isoformat()}")

        hist_df = my_yf.download(
            symbol,
            start=request_start.isoformat(),
            end=(limit_date + datetime.timedelta(days=1)).isoformat(),
            threads=False
        )

        if hist_df is None or hist_df.empty:
            print(f"[{currency}] No data returned for {symbol}.")
            continue

        if isinstance(hist_df.columns, pd.MultiIndex):
            if symbol in hist_df.columns.levels[0]:
                history = hist_df[symbol].dropna(subset=["Close"])
            else:
                history = pd.DataFrame()
        else:
            history = hist_df.dropna(subset=["Close"]) if "Close" in hist_df.columns else pd.DataFrame()

        downloaded_count = len(history.index) if not history.empty else 0
        print(f"[{currency}] Number of fx rates downloaded (rows with Close): {downloaded_count}")

        if history.empty:
            print(f"[{currency}] No Close prices available for {symbol}.")
            continue

        gap_data = fetch_and_fill_price_gaps(symbol, request_start, limit_date, history)
        after_gap_fill_total = len(gap_data)
        print(f"[{currency}] Number of fx rates after gap-filling (all calendar days): {after_gap_fill_total}")

        # filter out rows before fx_start and collect per-currency
        added_for_currency = 0
        for entry in gap_data:
            if entry["date"] < fx_start:
                continue

            rate_value = entry["value"] * 100 if currency == "GBX" else entry["value"]
            all_records.append({
                "currency": currency,
                "rate_date": entry["date"].isoformat(),
                "exchange_rate": float(rate_value),
                "rate_date_original": entry["origin"].isoformat()
            })
            added_for_currency += 1

        print(f"[{currency}] Number of fx rates after removing rows before fx_start (to consider for DB): {added_for_currency}")

    if not all_records:
        print("No FX records to process after filling gaps.")
        return

    min_date = min(pd.to_datetime(rec["rate_date"]).date() for rec in all_records)
    currencies = sorted({rec["currency"] for rec in all_records})
    existing_rows = database.get_fx_rates_for_currency_dates(currencies, min_date, limit_date, use_admin=True)
    existing_map = {}
    for row in existing_rows:
        normalized_rate_date = _normalize_fx_rate_date(row.get("rate_date"))
        normalized_rate_date_original = _normalize_fx_rate_date(row.get("rate_date_original"))
        normalized_exchange_rate = _normalize_fx_rate_value(row.get("exchange_rate"))

        if row.get("currency") and normalized_rate_date is not None:
            existing_map[(row["currency"], normalized_rate_date)] = (
                normalized_exchange_rate,
                normalized_rate_date_original
            )

    upsert_records = []
    for record in all_records:
        key = (record["currency"], record["rate_date"])
        existing = existing_map.get(key)
        if existing and existing[0] == record["exchange_rate"] and existing[1] == record["rate_date_original"]:
            continue
        record["updated_at"] = datetime.datetime.utcnow().isoformat()
        upsert_records.append(record)

    if not upsert_records:
        print("Everything is up to date. No changed or new FX rows to insert.")
        return

    # Print per-currency upsert counts for visibility
    from collections import Counter
    upsert_counter = Counter([r["currency"] for r in upsert_records])
    for cur, cnt in upsert_counter.items():
        print(f"[{cur}] Number of fx rates to upsert after deduplication: {cnt}")

    try:
        database.save_fx_rates_bulk(upsert_records)
        print(f"Successfully upserted {len(upsert_records)} FX records into Supabase.")
    except Exception as e:
        print(f"Database Error while saving records: {e}")
        sys.exit(1)

if __name__ == "__main__":
    headless_load_missing_fx_rates()

