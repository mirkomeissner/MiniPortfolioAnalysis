from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import src.database as database


CANONICAL_ASSET_COMPARE_FIELDS = [
    "price_close",
    "price_date_original",
    "dividend_cash",
    "split_factor",
]

CANONICAL_ASSET_FILLED_DEFAULTS = {
    "dividend_cash": 0.0,
    "split_factor": 1.0,
}


def normalize_float(value: Any, decimals: int = 10) -> Optional[float]:
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.strip().replace(" ", "")
            if value == "":
                return None
            # Basic locale-aware cleanup: 1.234,56 -> 1234.56
            if "," in value and "." in value:
                if value.rfind(",") > value.rfind("."):
                    value = value.replace(".", "").replace(",", ".")
                else:
                    value = value.replace(",", "")
            elif "," in value:
                value = value.replace(",", ".")
        parsed = float(value)
        return round(parsed, decimals)
    except Exception:
        return None


def normalize_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str):
            raw = value.strip()
            if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
                return datetime.fromisoformat(raw[:10]).date().isoformat()
        return pd.to_datetime(value, dayfirst=True).date().isoformat()
    except Exception:
        return None


def normalize_value(value: Any, value_type: str, decimals: int = 10) -> Any:
    if value_type == "float":
        return normalize_float(value, decimals=decimals)
    if value_type == "date":
        return normalize_date(value)
    if value_type == "str":
        if value is None:
            return None
        as_str = str(value).strip()
        return as_str if as_str != "" else None
    return value


def calculate_request_start_date(
    asset_start: Optional[date],
    bounds: Optional[Dict[str, Optional[date]]],
    lookback_days: int = 7,
    refresh_days: int = 35,
) -> Optional[date]:
    if asset_start is None:
        return None

    if not bounds:
        return asset_start - timedelta(days=lookback_days)

    min_date = bounds.get("min") or bounds.get("min_date")
    max_date = bounds.get("max") or bounds.get("max_date")

    if max_date is None:
        return asset_start - timedelta(days=lookback_days)

    if min_date is None or asset_start < min_date:
        return asset_start - timedelta(days=lookback_days)

    return max_date - timedelta(days=refresh_days)


def calculate_gap_fill_end_date(
    source_max_date: Optional[date],
    run_date: Optional[date] = None,
    lag_days: int = 1,
) -> Optional[date]:
    """
    Generic policy for gap-fill upper boundary used by any data provider.
    - run boundary: run_date - lag_days (usually yesterday)
    - final boundary: max(source_max_date, run boundary)
    """
    if source_max_date is None:
        return None

    effective_run_date = run_date or date.today()
    run_boundary = effective_run_date - timedelta(days=lag_days)
    return max(source_max_date, run_boundary)


def compare_and_deduplicate(
    loaded_records: List[Dict[str, Any]],
    existing_records: Iterable[Dict[str, Any]],
    key_fields: List[str],
    compare_fields: List[str],
    normalizers: Optional[Dict[str, Callable[[Any], Any]]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    normalizers = normalizers or {}

    def _norm(field: str, value: Any) -> Any:
        fn = normalizers.get(field)
        if fn is not None:
            return fn(value)
        if field.endswith("_date") or field.endswith("_date_original"):
            return normalize_date(value)
        return value

    existing_map: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    for row in existing_records:
        key = tuple(_norm(f, row.get(f)) for f in key_fields)
        existing_map[key] = row

    upsert_records: List[Dict[str, Any]] = []
    unchanged = 0
    changed = 0
    new = 0

    for rec in loaded_records:
        key = tuple(_norm(f, rec.get(f)) for f in key_fields)
        existing = existing_map.get(key)
        if existing is None:
            new += 1
            upsert_records.append(rec)
            continue

        same = True
        for f in compare_fields:
            if _norm(f, rec.get(f)) != _norm(f, existing.get(f)):
                same = False
                break

        if same:
            unchanged += 1
        else:
            changed += 1
            upsert_records.append(rec)

    return upsert_records, {
        "loaded": len(loaded_records),
        "new": new,
        "changed": changed,
        "unchanged": unchanged,
        "to_upsert": len(upsert_records),
    }


def gap_fill_asset_price_rows(
    canonical_rows: List[Dict[str, Any]],
    request_start_date: Optional[date],
    run_date: Optional[date] = None,
    lag_days: int = 1,
    filled_defaults: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Forward-fill canonical asset price rows across calendar days.

    Filled rows inherit the last known close and original source date while
    provider-specific event fields fall back to the supplied defaults.
    """
    if not canonical_rows:
        return [], {
            "after_gap_fill": 0,
            "fill_start_date": request_start_date.isoformat() if request_start_date else None,
            "fill_end_date": None,
        }

    filled_defaults = filled_defaults or CANONICAL_ASSET_FILLED_DEFAULTS

    normalized_rows: Dict[date, Dict[str, Any]] = {}
    for row in canonical_rows:
        row_date = _parse_date(row.get("price_date"))
        if row_date is None:
            continue

        normalized_row = dict(row)
        normalized_row["price_date"] = row_date.isoformat()
        price_date_original = _parse_date(normalized_row.get("price_date_original"))
        normalized_row["price_date_original"] = (
            price_date_original.isoformat() if price_date_original else row_date.isoformat()
        )
        normalized_rows[row_date] = normalized_row

    if not normalized_rows:
        return [], {
            "after_gap_fill": 0,
            "fill_start_date": request_start_date.isoformat() if request_start_date else None,
            "fill_end_date": None,
        }

    source_dates = sorted(normalized_rows.keys())
    start_date = request_start_date or source_dates[0]
    source_max_date = source_dates[-1]
    fill_end_date = calculate_gap_fill_end_date(
        source_max_date=source_max_date,
        run_date=run_date,
        lag_days=lag_days,
    )

    filled_rows: List[Dict[str, Any]] = []
    last_row: Optional[Dict[str, Any]] = None

    for current_day in pd.date_range(start=start_date, end=fill_end_date, freq="D").date:
        current_row = normalized_rows.get(current_day)
        if current_row is not None:
            last_row = dict(current_row)
            filled_rows.append(dict(current_row))
            continue

        if last_row is None:
            continue

        gap_row = dict(last_row)
        gap_row["price_date"] = current_day.isoformat()
        gap_row["price_date_original"] = last_row.get("price_date_original") or last_row.get("price_date")
        for field, default_value in filled_defaults.items():
            gap_row[field] = default_value
        filled_rows.append(gap_row)

    return filled_rows, {
        "after_gap_fill": len(filled_rows),
        "fill_start_date": start_date.isoformat(),
        "fill_end_date": fill_end_date.isoformat() if fill_end_date else None,
    }


def plan_asset_price_requests(
    assets: Iterable[Dict[str, Any]],
    bounds_map: Dict[str, Dict[str, Optional[date]]],
    lookback_days: int = 7,
    refresh_days: int = 35,
) -> List[Dict[str, Any]]:
    """
    Plan asset price requests by grouping assets by ISIN, selecting the minimum asset_start_date,
    and computing request_start_date using bounds and refresh policy.
    
    Args:
        assets: List of asset records from database.get_assets_by_price_source()
        bounds_map: Dict mapping ISIN to bounds from database.get_asset_price_bounds()
        lookback_days: Days to look back from asset_start if no bounds available
        refresh_days: Days to refresh from max_date if bounds available
    
    Returns:
        List of request plans, each with keys: isin, ticker, price_currency, asset_start_date, request_start_date
    """
    # Group by ISIN, select min asset_start_date
    grouped = {}
    for asset in assets:
        isin = asset.get("isin")
        ticker = asset.get("ticker")
        if not isin:
            continue
        
        price_start_date_str = asset.get("price_start_date")
        try:
            if isinstance(price_start_date_str, date):
                start_dt = price_start_date_str
            else:
                start_dt = pd.to_datetime(price_start_date_str).date() if price_start_date_str else None
        except Exception:
            start_dt = None
        
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
    
    # Build request plans with computed request_start_date
    plans = []
    for isin, item in grouped.items():
        asset_start = item.get("asset_start")
        if asset_start is None:
            continue  # Skip assets without a start date
        
        bounds = bounds_map.get(isin)
        request_start = calculate_request_start_date(
            asset_start=asset_start,
            bounds=bounds,
            lookback_days=lookback_days,
            refresh_days=refresh_days,
        )
        
        if request_start is not None:
            plans.append({
                "isin": isin,
                "ticker": item.get("ticker"),
                "price_currency": item.get("price_currency"),
                "asset_start_date": asset_start,
                "request_start_date": request_start,
            })
    
    return plans


def reconcile_asset_price_data(
    isin: str,
    asset_start_date: date,
    request_start_date: date,
    canonical_rows: List[Dict[str, Any]],
    existing_rows: Optional[Iterable[Dict[str, Any]]] = None,
    key_fields: List[str] = None,
    compare_fields: List[str] = None,
    normalizers: Dict[str, Callable[[Any], Any]] = None,
    run_date: Optional[date] = None,
    lag_days: int = 1,
    filled_defaults: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Shared reconciliation logic for asset price data across all providers.
    
    Performs:
    1. Gap-fill rows across calendar days up to the shared fill boundary
    2. Trim rows with price_date < asset_start_date
    3. Compare/deduplicate against existing rows
    
    Args:
        isin: Asset ISIN identifier
        asset_start_date: Earliest date this asset has prices (trim boundary)
        request_start_date: Start date for the current request (for reference)
        canonical_rows: Processed rows from provider in canonical schema
        existing_rows: Current rows from database. When omitted, rows are fetched
            from database.get_asset_prices_for_isin() using the post-trim date range.
        key_fields: Fields to use for identifying duplicates (default: ["isin", "price_date"])
        compare_fields: Fields to compare for change detection
        normalizers: Functions to normalize values for comparison
    
    Returns:
        Tuple of (upsert_records, summary_dict) where summary includes:
        - number_fetched: rows after provider parse/request_start filtering
        - after_gap_fill: rows after calendar gap fill
        - number_trimmed: rows remaining after asset_start trim
        - inserted: new rows
        - changed: changed rows
        - unchanged: unchanged rows
        - after_dedup: rows to upsert
    """
    if key_fields is None:
        key_fields = ["isin", "price_date"]
    if compare_fields is None:
        compare_fields = CANONICAL_ASSET_COMPARE_FIELDS
    if normalizers is None:
        normalizers = {}
    
    number_fetched = len(canonical_rows)

    gap_filled_rows, gap_fill_summary = gap_fill_asset_price_rows(
        canonical_rows=canonical_rows,
        request_start_date=request_start_date,
        run_date=run_date,
        lag_days=lag_days,
        filled_defaults=filled_defaults,
    )
    after_gap_fill = len(gap_filled_rows)
    
    # Trim rows below asset_start_date
    trimmed_rows = [
        r for r in gap_filled_rows
        if _parse_date(r.get("price_date")) and _parse_date(r.get("price_date")) >= asset_start_date
    ]
    number_trimmed = len(trimmed_rows)
    trimmed_away = after_gap_fill - number_trimmed
    
    if not trimmed_rows:
        return [], {
            "number_fetched": number_fetched,
            "after_gap_fill": after_gap_fill,
            "number_trimmed": number_trimmed,
            "trimmed_away": trimmed_away,
            "inserted": 0,
            "changed": 0,
            "unchanged": 0,
            "after_dedup": 0,
            **gap_fill_summary,
        }

    if existing_rows is None:
        min_loaded = min(r["price_date"] for r in trimmed_rows)
        max_loaded = max(r["price_date"] for r in trimmed_rows)
        existing_rows = database.get_asset_prices_for_isin(
            isin,
            start_date=min_loaded,
            end_date=max_loaded,
        )
    
    # Compare and deduplicate
    upsert_records, compare_summary = compare_and_deduplicate(
        loaded_records=trimmed_rows,
        existing_records=existing_rows or [],
        key_fields=key_fields,
        compare_fields=compare_fields,
        normalizers=normalizers,
    )
    
    after_dedup = len(upsert_records)
    inserted = compare_summary["new"]
    changed = compare_summary["changed"]
    unchanged = compare_summary["unchanged"]
    
    return upsert_records, {
        "number_fetched": number_fetched,
        "after_gap_fill": after_gap_fill,
        "number_trimmed": number_trimmed,
        "trimmed_away": trimmed_away,
        "inserted": inserted,
        "changed": changed,
        "unchanged": unchanged,
        "after_dedup": after_dedup,
        **gap_fill_summary,
    }


def _parse_date(value: Any) -> Optional[date]:
    """Helper to parse date values to date objects."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        if isinstance(value, str):
            raw = value.strip()
            if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
                return datetime.fromisoformat(raw[:10]).date()
        return pd.to_datetime(value, dayfirst=True).date()
    except Exception:
        return None


def parse_iso_date(value: Any) -> Optional[date]:
    """
    Consolidated date parsing function exported for provider modules.
    Replaces the duplicated _parse_iso_date in each provider.
    
    Args:
        value: Value to parse (ISO string, date object, or other datetime-like)
    
    Returns:
        date object or None
    """
    return _parse_date(value)


def empty_provider_result(raw_fetched: int = 0, parsed: int = 0) -> Dict[str, Any]:
    """
    Factory function for canonical empty provider result structure.
    Consolidates the repeated empty result dicts across all providers.
    
    Args:
        raw_fetched: Number of raw records from API
        parsed: Number of records after parsing
    
    Returns:
        Canonical empty result dict
    """
    return {
        "parsed": parsed,
        "raw_fetched": raw_fetched,
        "number_fetched": parsed,
        "after_gap_fill": 0,
        "number_trimmed": parsed,
        "after_dedup": 0,
        "new": 0,
        "changed": 0,
        "unchanged": 0,
        "inserted": 0,
        "to_upsert": 0,
        "upserted": 0,
    }


def validate_provider_request(
    ticker: str,
    asset_start: Optional[date],
    request_start: Optional[date],
    api_key_env_var: str,
) -> Optional[Dict[str, str]]:
    """
    Consolidated validation for provider requests.
    Used by EODHD and TIINGO to avoid duplicating validation logic.
    
    Args:
        ticker: Asset ticker to validate
        asset_start: Asset start date to validate
        request_start: Request start date to validate
        api_key_env_var: Environment variable name for API key (e.g., "EODHD_API_KEY")
    
    Returns:
        Error dict if validation fails, None if all valid
    """
    import os
    
    if not ticker:
        return {"error": "missing_ticker"}
    if asset_start is None:
        return {"error": "missing_asset_start"}
    if request_start is None:
        return {"error": "missing_request_start"}
    
    app_env = os.getenv("APP_ENV", "main").lower()
    api_key = os.getenv(api_key_env_var)
    if app_env != "dev" and not api_key:
        # Extract provider name from env var (e.g., "TIINGO_API_KEY" -> "tiingo")
        provider_name = api_key_env_var.split("_")[0].lower()
        return {"error": f"missing_{provider_name}_api_key"}
    
    return None


def persist_price_records(
    isin: str,
    records: List[Dict[str, Any]],
    dry_run: bool = False,
    recon_summary: Optional[Dict[str, Any]] = None,
    parsed: int = 0,
    raw_fetched: int = 0,
) -> Dict[str, Any]:
    """
    Consolidated persistence logic for all providers.
    Handles dry-run mode, empty records, DB upsert, and error handling.
    
    Args:
        isin: Asset ISIN identifier
        records: Price records to persist
        dry_run: If True, skip database write
        recon_summary: Summary from reconcile_asset_price_data
        parsed: Count of parsed records
        raw_fetched: Count of raw fetched records
    
    Returns:
        Result dict with persistence outcome
    """
    recon_summary = recon_summary or {}
    after_dedup = recon_summary.get("after_dedup", len(records))
    number_trimmed = recon_summary.get("number_trimmed", parsed)
    number_fetched = recon_summary.get("number_fetched", parsed)
    
    result_base = {
        "parsed": number_trimmed,
        "number_fetched": number_fetched,
        "number_trimmed": number_trimmed,
        "to_upsert": len(records),
        "unchanged": recon_summary.get("unchanged", 0),
        "new": recon_summary.get("inserted", 0),
        "changed": recon_summary.get("changed", 0),
        "raw_fetched": raw_fetched,
        "after_gap_fill": recon_summary.get("after_gap_fill", number_trimmed),
        "after_dedup": after_dedup,
        "inserted": recon_summary.get("inserted", 0),
    }
    
    if dry_run:
        return {"dry_run": True, **result_base, "upserted": after_dedup}
    
    if not records:
        return {**result_base, "upserted": 0}
    
    try:
        now_iso = datetime.utcnow().isoformat()
        for row in records:
            row["updated_at"] = now_iso
        database.save_asset_prices_bulk(records)
        return {**result_base, "upserted": len(records)}
    except Exception as e:
        print(f"DB upsert error for {isin}: {e}")
        return {"error": str(e)}


def process_provider_batch(
    provider_code: str,
    import_func: Callable,
    dry_run: bool = False,
    lookback_days: int = 7,
    refresh_days: int = 35,
) -> Dict[str, Any]:
    """
    Generic orchestrator for processing all assets from a provider.
    Consolidates the 200+ duplicated lines across process_all_*_assets functions.
    
    Args:
        provider_code: Provider code (e.g., "EODHD", "TGO", "ISH")
        import_func: Provider-specific import function (e.g., import_eodhd_history_for_ticker)
        dry_run: If True, skip database writes
        lookback_days: Lookback days for new assets
        refresh_days: Refresh days for incremental updates
    
    Returns:
        Summary dict with aggregated results
    """
    assets = database.get_assets_by_price_source(provider_code)
    bounds_map = database.get_asset_price_bounds()
    
    plans = plan_asset_price_requests(
        assets=assets,
        bounds_map=bounds_map,
        lookback_days=lookback_days,
        refresh_days=refresh_days,
    )
    
    summary = {
        "detected_isins": len(plans),
        "processed": 0,
        "skipped": 0,
        "errors": [],
        "raw_fetched": 0,
        "number_fetched": 0,
        "after_gap_fill": 0,
        "number_trimmed": 0,
        "parsed": 0,
        "to_upsert": 0,
        "upserted": 0,
        "inserted": 0,
        "changed": 0,
        "unchanged": 0,
    }
    
    print(f"{provider_code}: detected {len(plans)} relevant ISINs.")
    
    for plan in plans:
        isin = plan.get("isin")
        ticker = plan.get("ticker")
        asset_start = parse_iso_date(plan.get("asset_start_date"))
        request_start = parse_iso_date(plan.get("request_start_date"))
        price_currency = plan.get("price_currency")
        
        result = import_func(
            isin=isin,
            ticker=ticker,
            price_currency=price_currency,
            price_start_date=asset_start.isoformat() if asset_start else None,
            dry_run=dry_run,
            request_start_date=request_start.isoformat() if request_start else None,
            asset_start_date=asset_start.isoformat() if asset_start else None,
        )
        
        _accumulate_provider_result(summary, result, isin, ticker, request_start, provider_code)
    
    return summary


def _accumulate_provider_result(
    summary: Dict[str, Any],
    result: Dict[str, Any],
    isin: str,
    ticker: Optional[str],
    request_start: Optional[date],
    provider_code: str,
) -> None:
    """
    Helper to accumulate individual provider result into batch summary.
    
    Args:
        summary: Batch summary dict to update (modified in-place)
        result: Individual import result
        isin: Asset ISIN
        request_start: Request start date
        provider_code: Provider code for logging
    """
    summary["processed"] += 1

    if result.get("skipped"):
        summary["skipped"] += 1
        log_str = (
            f"[{provider_code}][{ticker or 'N/A'}][{isin}] request_start={request_start.isoformat() if request_start else 'N/A'} "
            f"skipped=True reason={result.get('reason', 'unspecified')}"
        )
        print(log_str)
        return

    summary["raw_fetched"] += int(result.get("raw_fetched", 0) or 0)
    summary["number_fetched"] += int(result.get("number_fetched", result.get("parsed", 0)) or 0)
    summary["after_gap_fill"] += int(result.get("after_gap_fill", 0) or 0)
    summary["number_trimmed"] += int(result.get("number_trimmed", result.get("parsed", 0)) or 0)
    summary["parsed"] += int(result.get("parsed", result.get("number_trimmed", 0)) or 0)
    summary["to_upsert"] += int(result.get("to_upsert", 0) or 0)
    summary["upserted"] += int(result.get("upserted", 0) or 0)
    summary["inserted"] += int(result.get("inserted", result.get("new", 0)) or 0)
    summary["changed"] += int(result.get("changed", 0) or 0)
    summary["unchanged"] += int(result.get("unchanged", 0) or 0)
    
    log_str = (
        f"[{provider_code}][{ticker or 'N/A'}][{isin}] request_start={request_start.isoformat() if request_start else 'N/A'} "
        f"number_fetched={int(result.get('number_fetched', result.get('parsed', 0)) or 0)} "
        f"number_trimmed={int(result.get('number_trimmed', result.get('parsed', 0)) or 0)} "
        f"inserted={int(result.get('inserted', result.get('new', 0)) or 0)} "
        f"changed={int(result.get('changed', 0) or 0)}"
    )
    print(log_str)
    
    if result.get("error"):
        summary["errors"].append({"isin": isin, "error": result.get("error")})
