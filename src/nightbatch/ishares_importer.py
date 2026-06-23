"""
Compatibility shim: imports from the new ishares_update module.
This file is deprecated; use ishares_update.py directly for new code.
"""
from src.nightbatch.ishares_update import (
    import_ishares_history_for_ticker,
    process_all_ishares_assets,
    _download_excel,
    ISHARE_URL_TEMPLATE,
)
from src.utils import parse_iso_date

__all__ = [
    "import_ishares_history_for_ticker",
    "process_all_ishares_assets",
    "_download_excel",
    "parse_iso_date",
    "ISHARE_URL_TEMPLATE",
]
