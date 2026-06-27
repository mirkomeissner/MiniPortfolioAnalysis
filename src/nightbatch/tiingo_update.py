import os
import pandas as pd
from datetime import date, datetime

import src.database as database
database.initialize_runtime_from_env(strict=False)
from src.utils import (
    my_tiingo,
    normalize_float,
    normalize_date,
    reconcile_asset_price_data,
    parse_iso_date,
    empty_provider_result,
    validate_provider_request,
    persist_price_records,
    process_provider_batch,
)


def _fetch_tiingo_history(ticker: str, api_key: str, request_start_date: date, timeout: int = 15):
    return my_tiingo.fetch_history(
        ticker_symbol=ticker,
        api_key=api_key,
        request_start_date=request_start_date,
        timeout=timeout,
    )


def import_tiingo_history_for_ticker(
    isin: str,
    ticker: str,
    price_currency: str,
    price_start_date: str = None,
    dry_run: bool = False,
    request_start_date: str = None,
    asset_start_date: str = None,
):
    """Downloads and imports TIINGO EOD price history for a single asset."""
    request_start = parse_iso_date(request_start_date)
    asset_start = parse_iso_date(asset_start_date) or parse_iso_date(price_start_date)

    # Use shared validation helper
    validation_error = validate_provider_request(
        ticker=ticker,
        asset_start=asset_start,
        request_start=request_start,
        api_key_env_var="TIINGO_API_KEY",
    )
    if validation_error:
        return validation_error

    try:
        rows = _fetch_tiingo_history(ticker=ticker, api_key=os.getenv("TIINGO_API_KEY"), request_start_date=request_start)
    except Exception as e:
        print(f"Failed to download TIINGO data for {ticker}: {e}")
        return {"error": str(e)}

    raw_fetched = len(rows)

    if not rows:
        return empty_provider_result(raw_fetched=raw_fetched)

    provider_df = pd.DataFrame(rows)
    if provider_df.empty:
        return empty_provider_result(raw_fetched=raw_fetched)

    required_fields = ["date", "close", "divCash", "splitFactor"]
    missing_fields = [f for f in required_fields if f not in provider_df.columns]
    if missing_fields:
        return {"error": f"missing_tiingo_columns:{','.join(missing_fields)}"}

    provider_df["price_date"] = pd.to_datetime(provider_df["date"], errors="coerce").dt.date
    provider_df["price_close"] = pd.to_numeric(provider_df["close"], errors="coerce")
    provider_df["dividend_cash"] = pd.to_numeric(provider_df["divCash"], errors="coerce").fillna(0.0)
    provider_df["split_factor"] = pd.to_numeric(provider_df["splitFactor"], errors="coerce").fillna(1.0)
    provider_df = provider_df.dropna(subset=["price_date", "price_close"]).copy()

    # Keep only requested range before gap fill to avoid unnecessary processing.
    provider_df = provider_df[provider_df["price_date"] >= request_start].copy()
    if provider_df.empty:
        return empty_provider_result(raw_fetched=raw_fetched)

    # Build canonical records from provider data
    canonical_records = []

    for idx, row in provider_df.iterrows():
        row_date = row["price_date"]
        canonical_records.append({
            "isin": isin,
            "price_date": row_date.isoformat(),
            "price_close": normalize_float(row["price_close"], decimals=10),
            "price_date_original": row_date.isoformat(),
            "dividend_cash": normalize_float(row["dividend_cash"], decimals=10) or 0.0,
            "split_factor": normalize_float(row["split_factor"], decimals=10) or 1.0,
        })

    parsed = len(canonical_records)
    if parsed == 0:
        return empty_provider_result(raw_fetched=raw_fetched)

    # Use shared reconciliation helper for gap-fill, trim, DB lookup, and dedup
    upsert_records, recon_summary = reconcile_asset_price_data(
        isin=isin,
        asset_start_date=asset_start,
        request_start_date=request_start,
        canonical_rows=canonical_records,
        key_fields=["isin", "price_date"],
        compare_fields=["price_close", "price_date_original", "dividend_cash", "split_factor"],
        normalizers={
            "price_date": normalize_date,
            "price_date_original": normalize_date,
            "price_close": lambda v: normalize_float(v, decimals=10),
            "dividend_cash": lambda v: normalize_float(v, decimals=10),
            "split_factor": lambda v: normalize_float(v, decimals=10),
        },
    )

    # Use shared persistence helper (handles dry-run, DB upsert, error handling)
    return persist_price_records(
        isin=isin,
        records=upsert_records,
        dry_run=dry_run,
        recon_summary=recon_summary,
        parsed=parsed,
        raw_fetched=raw_fetched,
    )


def process_all_tiingo_assets(dry_run: bool = False):
    """Process all TIINGO assets using the generic batch processor."""
    return process_provider_batch("TGO", import_tiingo_history_for_ticker, dry_run)


if __name__ == "__main__":
    process_all_tiingo_assets(dry_run=False)
