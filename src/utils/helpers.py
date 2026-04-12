import streamlit as st
from src.database import get_ref_options, get_country_region_map

def extract_code(label: str) -> str:
    """
    Extracts the code part from a label string like 'EQU (Equity)'.
    Returns 'EQU' in this case.
    """
    if not label or not isinstance(label, str):
        return label
    return label.split(" (")[0]

def get_option_index(options: list, current_code: str) -> int:
    """
    Finds the index of a code within a list of labels (e.g., finding 'STO' in ['STO (Stock)', ...]).
    """
    if not current_code:
        return 0
    try:
        return next(i for i, s in enumerate(options) if s.startswith(current_code))
    except (StopIteration, AttributeError):
        return 0

def ensure_reference_data():
    """
    Ensures that all necessary reference data is loaded into the session state.
    Reduces redundant database calls across different views.
    """
    if 'ref_data_loaded' not in st.session_state:
        with st.spinner("Loading reference data..."):
            st.session_state['opt_asset'] = get_ref_options("ref_asset_class")
            st.session_state['opt_gics'] = get_ref_options("ref_sector")
            st.session_state['opt_region'] = get_ref_options("ref_region")
            st.session_state['opt_type'] = get_ref_options("ref_instrument_type")
            st.session_state['opt_source'] = get_ref_options("ref_price_source")
            st.session_state['db_region_map'] = get_country_region_map()
            st.session_state['ref_data_loaded'] = True

      
