import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from src.utils import ensure_reference_data, extract_code, yfinance_search_component
from src.database import save_asset_static_data, get_ref_options, get_country_region_map

# --- 0. HELPER FUNCTIONS ---

# Helper functions moved to ui_components.py

# --- 2. helper functions for UI ---


def handle_save_request(row, isin):
    # Wir nutzen hier die extract_code Funktion aus deinen utils
    # um sicherzustellen, dass nur 'EQU' statt 'EQU (Equity)' gespeichert wird.
    # Wir ziehen die UUID des Users, da dein neues Schema UUID erwartet
    current_user_id = st.session_state.get('user_id')
    
    asset_entry = {
        "isin": isin,
        "name": row["Name"],
        "currency": row["Currency"],
        "ticker": row["Ticker"],
        "price_start_date": datetime.now().date().isoformat(),
        "price_source_code": "YFN",
        "instrument_type_code": extract_code(row["InstrumentType"]),
        "asset_class_code": extract_code(row["AssetClass"]),
        "region_code": extract_code(row["Region"]),
        "sector_code": extract_code(row["Sector_GICS"]),
        "industry": row["Industry"],
        "country": row["Country"],
        "created_by": current_user_id,
        "updated_by": None
    }

    try:
        save_asset_static_data(asset_entry)
        st.success(f"✅ {row['Ticker']} saved successfully!")
        
        # WICHTIG: Cache leeren, damit das neue Asset sofort in der Liste erscheint
        st.cache_data.clear()
        
        # Zurück zur Listenansicht
        st.session_state["view"] = "list" 
        st.rerun() 
    except Exception as e:
        st.error(f"Error saving data: {e}")



def ticker_search_view():
    st.subheader("🔍 Search New Asset")
    ensure_reference_data()

    # Flexible search input
    search_input = st.text_input("Enter ISIN, Ticker or Name", placeholder="e.g. AU000000DRO2 or Apple")
    
    selected_row, edited_df = yfinance_search_component(search_input, session_key_prefix="ticker_search", allow_isin_edit=True)
    
    if selected_row is not None and edited_df is not None:
        if st.button("Save to Database", type="primary"):
            if not selected_row["ISIN"] or len(selected_row["ISIN"]) < 5:
                st.error("Please enter a valid ISIN in the table above before saving.")
            else:
                handle_save_request(selected_row, selected_row["ISIN"])


    


    


