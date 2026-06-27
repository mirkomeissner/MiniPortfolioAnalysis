# Expose utility functions at the package level
from .helpers import (
    extract_code, 
    get_option_index, 
    get_option_index_by_label,
    get_selectbox_options_and_index,
    ensure_reference_data, 
    reset_reference_data,
    fetch_and_fill_price_gaps
)
from .ui_components import (
    apply_advanced_filters, 
    get_average_volume_7d, 
    map_yahoo_to_ref, 
    map_yahoo_to_instrument_type, 
    map_yahoo_to_asset_class, 
    yfinance_search_component
)
from .yf_wrapper import my_yf
from .tiingo_wrapper import my_tiingo
from .eodhd_wrapper import my_eodhd
from .ishares_wrapper import my_ishares
from .email_service import send_duplicate_info_mail
from .data_import_helpers import (
    normalize_float,
    normalize_date,
    normalize_value,
    calculate_request_start_date,
    calculate_gap_fill_end_date,
    compare_and_deduplicate,
    plan_asset_price_requests,
    reconcile_asset_price_data,
    parse_iso_date,
    empty_provider_result,
    validate_provider_request,
    persist_price_records,
    process_provider_batch,
)

__all__ = [
    'extract_code',
    'get_option_index',
    'get_option_index_by_label',
    'get_selectbox_options_and_index',
    'ensure_reference_data',
    'reset_reference_data',
    'fetch_and_fill_price_gaps',
    'apply_advanced_filters',
    'get_average_volume_7d',
    'map_yahoo_to_ref',
    'map_yahoo_to_instrument_type',
    'map_yahoo_to_asset_class',
    'yfinance_search_component',
    'my_yf',
    'my_tiingo',
    'my_eodhd',
    'my_ishares',
    'send_duplicate_info_mail',
    'normalize_float',
    'normalize_date',
    'normalize_value',
    'calculate_request_start_date',
    'calculate_gap_fill_end_date',
    'compare_and_deduplicate',
]
