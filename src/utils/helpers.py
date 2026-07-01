import streamlit as st
import pandas as pd
from src.utils.backend_api_client import fetch_reference_data_bundle



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

def get_option_index_by_label(options: list, current_label: str):
    """
    Finds the index of a label within a list of formatted options (e.g., finding 'Energy' in ['10 (Energy)', ...]).
    For null/empty labels, returns 0 to select a placeholder option.
    """
    if not current_label:
        return 0
    try:
        return next(i for i, s in enumerate(options) if s == current_label or f"({current_label})" in s)
    except (StopIteration, AttributeError):
        return 0

def get_selectbox_options_and_index(options: list, current_label: str):
    """
    Returns options list and index for selectbox, always including a null option.
    Adds a "(None)" option at the beginning for setting values to null.
    """
    # Always add (None) option at the beginning
    enhanced_options = ["(None)"] + options

    if not current_label:
        return enhanced_options, 0

    # Look for the current label in the original options (not the enhanced ones)
    try:
        index = next(i for i, s in enumerate(options) if s == current_label or f"({current_label})" in s)
        return enhanced_options, index + 1  # +1 because (None) is at index 0
    except (StopIteration, AttributeError):
        return enhanced_options, 0

def ensure_reference_data():
    """
    Zentrale Funktion, um sicherzustellen, dass ALLE Dropdown-Optionen
    im Session State vorhanden sind.
    """
    # Wir prüfen, ob der User überhaupt eingeloggt ist, bevor wir laden
    user_id = st.session_state.get("user_id")
    
    if 'ref_data_loaded' not in st.session_state and user_id:
        with st.spinner("Loading reference data..."):
            bundle = fetch_reference_data_bundle(user_id)

            st.session_state['opt_asset'] = bundle.get('opt_asset', [])
            st.session_state['opt_gics'] = bundle.get('opt_gics', [])
            st.session_state['opt_region'] = bundle.get('opt_region', [])
            st.session_state['opt_type'] = bundle.get('opt_type', [])
            st.session_state['opt_source'] = bundle.get('opt_source', [])
            st.session_state['opt_trans_types'] = bundle.get('opt_trans_types', [])
            st.session_state['opt_accounts'] = bundle.get('opt_accounts', [])
            st.session_state['opt_assets'] = bundle.get('opt_assets', [])
            st.session_state['db_region_map'] = bundle.get('db_region_map', {})
            st.session_state['type_logic_map'] = bundle.get('type_logic_map', {})
            
            # Flag setzen
            st.session_state['ref_data_loaded'] = True

def reset_reference_data():
    """Hilfsfunktion, um den Cache zu leeren (z.B. nach Account-Erstellung)"""
    if 'ref_data_loaded' in st.session_state:
        del st.session_state['ref_data_loaded']


def fetch_and_fill_price_gaps(symbol, start_date, end_date, source_df):
    """Fill calendar gaps from a pre-fetched DataFrame containing Close prices."""
    if source_df is None or source_df.empty:
        return []

    df = source_df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        normalized_columns = []
        for c in df.columns:
            if isinstance(c, tuple) and c:
                normalized_columns.append(str(c[0]).capitalize())
            else:
                normalized_columns.append(str(c).capitalize())
        df.columns = normalized_columns
    else:
        df.columns = [str(c).capitalize() for c in df.columns]
    df.index = pd.to_datetime(df.index).date

    results = []
    last_valid_rate = None
    last_valid_origin = None

    hist_before = df[df.index <= start_date]
    if not hist_before.empty:
        last_valid_rate = float(hist_before.iloc[-1]["Close"])
        last_valid_origin = hist_before.index[-1]

    for current_day in pd.date_range(start=start_date, end=end_date, freq='D').date:
        if current_day in df.index:
            last_valid_rate = float(df.loc[current_day, "Close"])
            last_valid_origin = current_day

        if last_valid_rate is not None:
            results.append({
                "date": current_day,
                "value": last_valid_rate,
                "origin": last_valid_origin
            })

    return results

