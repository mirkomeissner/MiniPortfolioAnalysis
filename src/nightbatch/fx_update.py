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


# 2. INTERNE MODULE IMPORTIEREN (Jetzt weiß Python, wo 'src' liegt)
# -------------------------------------------------------------------------



# Now it's safe to import internal modules
import src.database as database
database.initialize_runtime_from_env(strict=False)
from src.utils import (
    my_yf,
    fetch_and_fill_price_gaps,
    normalize_float,
    normalize_date,
    calculate_request_start_date,
    calculate_gap_fill_end_date,
    compare_and_deduplicate,
)


def headless_load_missing_fx_rates(dry_run: bool = False):
    """
    Orchestrates an API-efficient FX update process.
    - Uses a 7-day window for normal incremental daily updates.
    - Automatically falls back to full history mode if a currency is new 
      or has a large database gap (> 7 days).
    """
    print(f"Starting API-optimized automated FX rates update (dry_run={dry_run})...")

    # Fetch required start dates from assets and existing bounds from DB
    target_starts_raw = database.get_non_eur_asset_currency_start_dates()
    current_bounds = database.get_fx_rate_bounds()

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

        request_start = calculate_request_start_date(
            asset_start=fx_start,
            bounds=bounds,
            lookback_days=7,
            refresh_days=35,
        )

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
            level0 = hist_df.columns.get_level_values(0)
            level1 = hist_df.columns.get_level_values(1)
            if symbol in level1:
                history = hist_df.xs(symbol, axis=1, level=1).dropna(subset=["Close"])
            elif symbol in level0:
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

        source_max_date = pd.to_datetime(history.index).max().date()
        fill_end_date = calculate_gap_fill_end_date(
            source_max_date=source_max_date,
            run_date=today,
            lag_days=1,
        )

        gap_data = fetch_and_fill_price_gaps(symbol, request_start, fill_end_date, history)
        after_gap_fill_total = len(gap_data)
        print(f"[{currency}] Number of fx rates after gap-filling (all calendar days): {after_gap_fill_total}")

        # filter out rows before fx_start and collect per-currency
        added_for_currency = 0
        for entry in gap_data:
            if entry["date"] < fx_start:
                continue

            rate_value = entry["value"] * 100 if currency == "GBX" else entry["value"]
            exchange_rate = normalize_float(rate_value, decimals=10)
            all_records.append({
                "currency": currency,
                "rate_date": entry["date"].isoformat(),
                "exchange_rate": exchange_rate,
                "rate_date_original": entry["origin"].isoformat()
            })
            added_for_currency += 1

        print(f"[{currency}] Number of fx rates after removing rows before fx_start (to consider for DB): {added_for_currency}")

    if not all_records:
        print("No FX records to process after filling gaps.")
        return

    min_date = min(pd.to_datetime(rec["rate_date"]).date() for rec in all_records)
    max_date = max(pd.to_datetime(rec["rate_date"]).date() for rec in all_records)
    currencies = sorted({rec["currency"] for rec in all_records})
    existing_rows = database.get_fx_rates_for_currency_dates(currencies, min_date, max_date)
    upsert_records, compare_summary = compare_and_deduplicate(
        loaded_records=all_records,
        existing_records=existing_rows,
        key_fields=["currency", "rate_date"],
        compare_fields=["exchange_rate", "rate_date_original"],
        normalizers={
            "rate_date": normalize_date,
            "rate_date_original": normalize_date,
            "exchange_rate": lambda v: normalize_float(v, decimals=10),
        },
    )
    print(
        "FX compare summary: "
        f"loaded={compare_summary['loaded']} new={compare_summary['new']} "
        f"changed={compare_summary['changed']} unchanged={compare_summary['unchanged']}"
    )

    for record in upsert_records:
        record["updated_at"] = datetime.datetime.utcnow().isoformat()

    if not upsert_records:
        print("Everything is up to date. No changed or new FX rows to insert.")
        return {"loaded": compare_summary["loaded"], "to_upsert": 0, "dry_run": dry_run}

    # Print per-currency upsert counts for visibility
    from collections import Counter
    upsert_counter = Counter([r["currency"] for r in upsert_records])
    for cur, cnt in upsert_counter.items():
        print(f"[{cur}] Number of fx rates to upsert after deduplication: {cnt}")

    if dry_run:
        print(f"DRY-RUN: Would upsert {len(upsert_records)} FX records into Supabase.")
        return {"loaded": compare_summary["loaded"], "to_upsert": len(upsert_records), "dry_run": True}

    try:
        database.save_fx_rates_bulk(upsert_records)
        print(f"Successfully upserted {len(upsert_records)} FX records into Supabase.")
        return {"loaded": compare_summary["loaded"], "upserted": len(upsert_records), "dry_run": False}
    except Exception as e:
        print(f"Database Error while saving records: {e}")
        sys.exit(1)

if __name__ == "__main__":
    headless_load_missing_fx_rates(dry_run=False)

