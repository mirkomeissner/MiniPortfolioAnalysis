"""
Compatibility shim: imports from the new eodhd_update module.
This file is deprecated; use eodhd_update.py directly for new code.
"""
from src.nightbatch.eodhd_update import (
    import_eodhd_history_for_ticker,
    process_all_eodhd_assets,
    _fetch_eodhd_history,
    EODHD_URL_TEMPLATE,
)
from src.utils import parse_iso_date

__all__ = [
    "import_eodhd_history_for_ticker",
    "process_all_eodhd_assets",
    "_fetch_eodhd_history",
    "parse_iso_date",
    "EODHD_URL_TEMPLATE",
]
