import streamlit as st
from src.database import (
    get_account_ref_options, 
    get_asset_ref_options, 
    get_ref_options,  
    get_country_region_map,
    get_transaction_type_logic
)
import datetime
import pandas as pd



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
            # 1. Allgemeine Stammdaten (aus dem 'shared' Schema)
            # Diese sind für alle User gleich
            st.session_state['opt_asset'] = get_ref_options("ref_asset_class")
            st.session_state['opt_gics'] = get_ref_options("ref_sector")
            st.session_state['opt_region'] = get_ref_options("ref_region")
            st.session_state['opt_type'] = get_ref_options("ref_instrument_type")
            st.session_state['opt_source'] = get_ref_options("ref_price_source")
            st.session_state['opt_trans_types'] = get_ref_options("ref_transaction_type")
            
            # 2. Spezifische Stammdaten
            # WICHTIG: Hier nutzen wir jetzt die user_id (UUID) statt user_name
            st.session_state['opt_accounts'] = get_account_ref_options(user_id)
            st.session_state['opt_assets'] = get_asset_ref_options()
            
            # 3. Hilfs-Maps
            st.session_state['db_region_map'] = get_country_region_map()
            st.session_state['type_logic_map'] = get_transaction_type_logic()
            
            # Flag setzen
            st.session_state['ref_data_loaded'] = True

def reset_reference_data():
    """Hilfsfunktion, um den Cache zu leeren (z.B. nach Account-Erstellung)"""
    if 'ref_data_loaded' in st.session_state:
        del st.session_state['ref_data_loaded']










def fetch_and_fill_gaps(symbol, start_date, end_date, yf_ticker_obj):
    """
    Generische Funktion zum Abruf von yfinance-Daten mit Gap-Filling.
    Gibt eine Liste von Records zurück.
    """
    records = []
    # 7-Tage-Puffer für die Initialisierung des ersten Kurses
    fetch_start = start_date - datetime.timedelta(days=7)
    
    history = yf_ticker_obj.history(
        start=fetch_start.isoformat(),
        end=(end_date + datetime.timedelta(days=1)).isoformat(),
        interval="1d"
    )
    
    if history is None or history.empty:
        return []

    history.columns = [c.capitalize() for c in history.columns]
    history.index = history.index.date
    
    last_valid_rate = None
    last_valid_origin = None

    # Initialisierung mit dem Puffer-Zeitraum
    hist_before = history[history.index <= start_date]
    if not hist_before.empty:
        last_valid_rate = float(hist_before.iloc[-1]["Close"])
        last_valid_origin = hist_before.index[-1]

    # Kalender-Loop über die eigentliche Lücke
    gap_days = pd.date_range(start=start_date, end=end_date, freq='D').date
    for current_day in gap_days:
        if current_day in history.index:
            last_valid_rate = float(history.loc[current_day, "Close"])
            last_valid_origin = current_day
        
        if last_valid_rate is not None:
            records.append({
                "date": current_day,
                "value": last_valid_rate,
                "origin": last_valid_origin
            })
    return records


