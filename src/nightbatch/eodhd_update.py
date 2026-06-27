import os
import pandas as pd
from datetime import date, datetime

import src.database as database
database.initialize_runtime_from_env(strict=False)
from src.utils import (
    my_eodhd,
    normalize_float,
    normalize_date,
    reconcile_asset_price_data,
    parse_iso_date,
    empty_provider_result,
    validate_provider_request,
    persist_price_records,
    process_provider_batch,
)


def _fetch_eodhd_history(ticker: str, api_key: str, request_start_date: date, timeout: int = 15):
    return my_eodhd.fetch_history(
        ticker=ticker,
        api_key=api_key,
        request_start_date=request_start_date,
        timeout=timeout,
    )


def import_eodhd_history_for_ticker(
    isin: str,
    ticker: str,
    price_currency: str,
    price_start_date: str = None,
    dry_run: bool = False,
    request_start_date: str = None,
    asset_start_date: str = None,
):
    """
    Downloads and imports EODHD EOD price history for a single asset.

    Dividend and split handling are intentionally fixed for now and isolated
    so dedicated endpoints can be integrated later with minimal refactoring.
    """
    request_start = parse_iso_date(request_start_date)
    asset_start = parse_iso_date(asset_start_date) or parse_iso_date(price_start_date)

    # Use shared validation helper
    validation_error = validate_provider_request(
        ticker=ticker,
        asset_start=asset_start,
        request_start=request_start,
        api_key_env_var="EODHD_API_KEY",
    )
    if validation_error:
        return validation_error

    try:
        rows = _fetch_eodhd_history(ticker=ticker, api_key=os.getenv("EODHD_API_KEY"), request_start_date=request_start)
    except Exception as e:
        print(f"Failed to download EODHD data for {ticker}: {e}")
        return {"error": str(e)}

    raw_fetched = len(rows)

    if not rows:
        return empty_provider_result(raw_fetched=raw_fetched)

    provider_df = pd.DataFrame(rows)
    if provider_df.empty:
        return empty_provider_result(raw_fetched=raw_fetched)

    date_col = "date" if "date" in provider_df.columns else "Date" if "Date" in provider_df.columns else None
    close_col = None
    for candidate in ["close", "Close", "adjusted_close", "Adjusted_close", "Adjusted_Close"]:
        if candidate in provider_df.columns:
            close_col = candidate
            break

    if date_col is None or close_col is None:
        return {"error": "missing_eodhd_columns"}

    provider_df["price_date"] = pd.to_datetime(provider_df[date_col], errors="coerce").dt.date
    provider_df["price_close"] = pd.to_numeric(provider_df[close_col], errors="coerce")
    provider_df = provider_df.dropna(subset=["price_date", "price_close"]).copy()

    # Keep only requested range before gap fill to avoid unnecessary processing.
    provider_df = provider_df[provider_df["price_date"] >= request_start].copy()
    if provider_df.empty:
        return empty_provider_result(raw_fetched=raw_fetched)

    # Build canonical records with EODHD-specific fixed dividend/split values
    canonical_records = []
    for idx, row in provider_df.iterrows():
        canonical_records.append({
            "isin": isin,
            "price_date": row["price_date"].isoformat(),
            "price_close": normalize_float(row["price_close"], decimals=10),
            "price_date_original": row["price_date"].isoformat(),
            "dividend_cash": 0.0,  # EODHD dividend/split endpoints not yet integrated
            "split_factor": 1.0,
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


def process_all_eodhd_assets(dry_run: bool = False):
    """Process all EODHD assets using the generic batch processor."""
    return process_provider_batch("EODHD", import_eodhd_history_for_ticker, dry_run)


if __name__ == "__main__":
    process_all_eodhd_assets(dry_run=False)
