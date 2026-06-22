import os
import requests
import pandas as pd
from datetime import date, datetime

import src.database as database
database.initialize_runtime_from_env(strict=False)
from src.utils import (
    fetch_and_fill_price_gaps,
    normalize_float,
    normalize_date,
    calculate_request_start_date,
    calculate_gap_fill_end_date,
    compare_and_deduplicate,
)


TIINGO_URL_TEMPLATE = "https://api.tiingo.com/tiingo/daily/{ticker}/prices"


def _parse_iso_date(value):
    if value is None:
        return None
    try:
        if isinstance(value, str):
            raw = value.strip()
            if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
                return datetime.fromisoformat(raw[:10]).date()
        return pd.to_datetime(value, dayfirst=True).date()
    except Exception:
        return None


def _fetch_tiingo_history(ticker: str, api_key: str, request_start_date: date, timeout: int = 15):
    params = {
        "startDate": request_start_date.isoformat(),
        "token": api_key,
    }
    response = requests.get(TIINGO_URL_TEMPLATE.format(ticker=ticker), params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []


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
    request_start = _parse_iso_date(request_start_date)
    asset_start = _parse_iso_date(asset_start_date) or _parse_iso_date(price_start_date)

    if not ticker:
        return {"error": "missing_ticker"}
    if asset_start is None:
        return {"error": "missing_asset_start"}
    if request_start is None:
        return {"error": "missing_request_start"}

    api_key = os.getenv("TIINGO_API_KEY")
    if not api_key:
        return {"error": "missing_tiingo_api_key"}

    try:
        rows = _fetch_tiingo_history(ticker=ticker, api_key=api_key, request_start_date=request_start)
    except Exception as e:
        print(f"Failed to download TIINGO data for {ticker}: {e}")
        return {"error": str(e)}

    raw_fetched = len(rows)

    if not rows:
        return {
            "parsed": 0,
            "raw_fetched": raw_fetched,
            "after_gap_fill": 0,
            "after_dedup": 0,
            "new": 0,
            "changed": 0,
            "inserted": 0,
            "upserted": 0,
        }

    provider_df = pd.DataFrame(rows)
    if provider_df.empty:
        return {"parsed": 0}

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
        return {
            "parsed": 0,
            "raw_fetched": raw_fetched,
            "after_gap_fill": 0,
            "after_dedup": 0,
            "new": 0,
            "changed": 0,
            "inserted": 0,
            "upserted": 0,
        }

    source_max_date = max(provider_df["price_date"])
    fill_end_date = calculate_gap_fill_end_date(
        source_max_date=source_max_date,
        run_date=date.today(),
        lag_days=1,
    )

    tmp_df = pd.DataFrame({"Close": provider_df.set_index("price_date")["price_close"]})
    gap_data = fetch_and_fill_price_gaps(ticker, request_start, fill_end_date, tmp_df)
    after_gap_fill = len(gap_data)

    # Dividends and splits are provider-native TIINGO fields keyed by actual provider date.
    div_map = {
        row["price_date"]: normalize_float(row["dividend_cash"], decimals=10) or 0.0
        for _, row in provider_df.iterrows()
    }
    split_map = {
        row["price_date"]: normalize_float(row["split_factor"], decimals=10) or 1.0
        for _, row in provider_df.iterrows()
    }

    records = []
    for entry in gap_data:
        row_date = entry["date"]
        if row_date < asset_start:
            continue

        records.append(
            {
                "isin": isin,
                "price_date": row_date.isoformat(),
                "price_close": normalize_float(entry["value"], decimals=10),
                "price_date_original": entry.get("origin", row_date).isoformat(),
                "dividend_cash": div_map.get(row_date, 0.0),
                "split_factor": split_map.get(row_date, 1.0),
            }
        )

    parsed = len(records)
    if parsed == 0:
        return {
            "parsed": 0,
            "raw_fetched": raw_fetched,
            "after_gap_fill": after_gap_fill,
            "after_dedup": 0,
            "new": 0,
            "changed": 0,
            "inserted": 0,
            "upserted": 0,
        }

    min_loaded = min(r["price_date"] for r in records)
    max_loaded = max(r["price_date"] for r in records)
    existing_rows = database.get_asset_prices_for_isin(isin, start_date=min_loaded, end_date=max_loaded)

    upsert_records, compare_summary = compare_and_deduplicate(
        loaded_records=records,
        existing_records=existing_rows,
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

    after_dedup = len(upsert_records)
    inserted_count = compare_summary["new"]
    changed_count = compare_summary["changed"]

    if dry_run:
        return {
            "parsed": parsed,
            "to_upsert": len(upsert_records),
            "unchanged": compare_summary["unchanged"],
            "new": compare_summary["new"],
            "changed": compare_summary["changed"],
            "raw_fetched": raw_fetched,
            "after_gap_fill": after_gap_fill,
            "after_dedup": after_dedup,
            "inserted": inserted_count,
            "upserted": after_dedup,
        }

    if not upsert_records:
        return {
            "parsed": parsed,
            "upserted": 0,
            "unchanged": compare_summary["unchanged"],
            "new": inserted_count,
            "changed": changed_count,
            "raw_fetched": raw_fetched,
            "after_gap_fill": after_gap_fill,
            "after_dedup": 0,
            "inserted": inserted_count,
        }

    try:
        now_iso = datetime.utcnow().isoformat()
        for row in upsert_records:
            row["updated_at"] = now_iso
        database.save_asset_prices_bulk(upsert_records)
        return {
            "parsed": parsed,
            "upserted": len(upsert_records),
            "unchanged": compare_summary["unchanged"],
            "new": compare_summary["new"],
            "changed": compare_summary["changed"],
            "raw_fetched": raw_fetched,
            "after_gap_fill": after_gap_fill,
            "after_dedup": after_dedup,
            "inserted": inserted_count,
        }
    except Exception as e:
        print(f"DB upsert error for {isin}: {e}")
        return {"error": str(e)}


def process_all_tiingo_assets(dry_run: bool = False):
    assets = database.get_assets_by_price_source("TGO")
    bounds_map = database.get_asset_price_bounds()

    grouped = {}
    for asset in assets:
        isin = asset.get("isin")
        ticker = asset.get("ticker")
        if not isin:
            continue

        start_dt = _parse_iso_date(asset.get("price_start_date"))
        if isin not in grouped:
            grouped[isin] = {
                "isin": isin,
                "ticker": ticker,
                "price_currency": asset.get("price_currency"),
                "asset_start": start_dt,
            }
        else:
            current_start = grouped[isin].get("asset_start")
            if start_dt is not None and (current_start is None or start_dt < current_start):
                grouped[isin]["asset_start"] = start_dt
            if not grouped[isin].get("ticker") and ticker:
                grouped[isin]["ticker"] = ticker
            if not grouped[isin].get("price_currency") and asset.get("price_currency"):
                grouped[isin]["price_currency"] = asset.get("price_currency")

    summary = {
        "detected_isins": 0,
        "processed": 0,
        "skipped": 0,
        "errors": [],
        "raw_fetched": 0,
        "after_gap_fill": 0,
        "parsed": 0,
        "to_upsert": 0,
        "upserted": 0,
        "inserted": 0,
        "changed": 0,
        "unchanged": 0,
    }

    summary["detected_isins"] = len(grouped)
    print(f"TIINGO: detected {summary['detected_isins']} relevant ISINs.")

    for isin, item in grouped.items():
        ticker = item.get("ticker")
        asset_start = item.get("asset_start")
        price_currency = item.get("price_currency")

        if not ticker or asset_start is None:
            summary["skipped"] += 1
            summary["errors"].append({"isin": isin, "error": "missing_ticker_or_asset_start"})
            continue

        bounds = bounds_map.get(isin)
        request_start = calculate_request_start_date(
            asset_start=asset_start,
            bounds=bounds,
            lookback_days=7,
            refresh_days=35,
        )

        result = import_tiingo_history_for_ticker(
            isin=isin,
            ticker=ticker,
            price_currency=price_currency,
            price_start_date=asset_start.isoformat() if asset_start else None,
            dry_run=dry_run,
            request_start_date=request_start.isoformat() if request_start else None,
            asset_start_date=asset_start.isoformat() if asset_start else None,
        )

        summary["processed"] += 1
        summary["raw_fetched"] += int(result.get("raw_fetched", 0) or 0)
        summary["after_gap_fill"] += int(result.get("after_gap_fill", 0) or 0)
        summary["parsed"] += int(result.get("parsed", 0) or 0)
        summary["to_upsert"] += int(result.get("to_upsert", 0) or 0)
        summary["upserted"] += int(result.get("upserted", 0) or 0)
        summary["inserted"] += int(result.get("inserted", result.get("new", 0)) or 0)
        summary["changed"] += int(result.get("changed", 0) or 0)
        summary["unchanged"] += int(result.get("unchanged", 0) or 0)

        print(
            f"[TIINGO][{isin}] request_start={request_start.isoformat()} "
            f"raw_fetched={int(result.get('raw_fetched', 0) or 0)} "
            f"after_gap_fill={int(result.get('after_gap_fill', 0) or 0)} "
            f"after_dedup={int(result.get('after_dedup', result.get('to_upsert', result.get('upserted', 0))) or 0)} "
            f"inserted={int(result.get('inserted', result.get('new', 0)) or 0)} "
            f"changed={int(result.get('changed', 0) or 0)}"
        )

        if result.get("error"):
            summary["errors"].append({"isin": isin, "error": result.get("error")})

    return summary


if __name__ == "__main__":
    process_all_tiingo_assets(dry_run=False)
