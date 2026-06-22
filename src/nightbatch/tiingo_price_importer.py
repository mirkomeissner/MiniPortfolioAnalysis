"""
Compatibility shim: imports from the new tiingo_update module.
This file is deprecated; use tiingo_update.py directly for new code.
"""
from src.nightbatch.tiingo_update import (
    import_tiingo_history_for_ticker,
    process_all_tiingo_assets,
    _fetch_tiingo_history,
    TIINGO_URL_TEMPLATE,
)
from src.utils import parse_iso_date

__all__ = [
    "import_tiingo_history_for_ticker",
    "process_all_tiingo_assets",
    "_fetch_tiingo_history",
    "parse_iso_date",
    "TIINGO_URL_TEMPLATE",
]
