from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd


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
