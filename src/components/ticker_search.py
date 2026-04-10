import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from src.database import supabase

# --- 1. HILFSFUNKTIONEN ---

def get_ref_data(table_name):
    """Holt Code und Label aus den REF-Tabellen und gibt ein Dictionary {code: "code (label)"} zurück."""
    try:
        response = supabase.table(table_name).select("code, label").execute()
        # Erstellt ein Mapping: {"EQU": "EQU (Equities & Equity Funds)", ...}
        return {item['code']: f"{item['code']} ({item['label']})" for item in response.data}
    except Exception as e:
        st.error(f"Error loading {table_name}: {e}")
        return {}

def get_country_mapping():
    try:
        response = supabase.table("country_region_mapping").select("country, region_code").execute()
        return {item['country']: item['region_code'] for item in response.data}
    except Exception as e:
        st.error(f"Error loading region mapping: {e}")
        return {}

# ... (map_yahoo_to_ref, map_yahoo_to_instrument_type, map_yahoo_to_asset_class bleiben identisch)

def ticker_search_view():
    st.title("🔍 Ticker Search & Edit")
    st.write("Suchen Sie per ISIN und passen Sie die Stammdaten an.")

    # REF-Daten initialisieren mit Labels
    if 'ref_data_loaded' not in st.session_state:
        with st.spinner("Lade Referenzdaten..."):
            st.session_state['db_region_map'] = get_country_mapping()
            
            # Wir speichern jetzt die ganzen Dictionaries {Code: "Code (Label)"}
            st.session_state['ref_sectors_dict'] = get_ref_data("ref_sector")
            st.session_state['ref_regions_dict'] = get_ref_data("ref_region")
            st.session_state['ref_instr_types_dict'] = get_ref_data("ref_instrument_type")
            st.session_state['ref_asset_classes_dict'] = get_ref_data("ref_asset_class")
            
            st.session_state['ref_data_loaded'] = True

    # Eingabe & Suche (identisch zu vorher...)
    col1, col2 = st.columns([3, 1])
    with col1:
        isin_input = st.text_input("ISIN eingeben", placeholder="z.B. US0378331005")
    with col2:
        st.write("##")
        search_button = st.button("Ticker suchen", use_container_width=True)

    if search_button and isin_input:
        # ... (Deine Yahoo Finance Suchlogik bleibt exakt gleich wie in der Vorversion)
        # Am Ende wird st.session_state["search_results_df"] befüllt.
        # [Hier den Such-Code aus der vorigen Antwort einfügen]
        pass 

    # --- EDITABLE TABLE AREA ---
    if "search_results_df" in st.session_state:
        st.subheader("Stammdaten verfeinern")
        
        # Hilfsfunktion für die Anzeige im Dropdown
        # Wir übergeben die Keys (Codes) als Optionen und nutzen das Dictionary zur Anzeige
        column_config = {
            "Ticker": st.column_config.TextColumn(disabled=True),
            "Name": st.column_config.TextColumn(disabled=True),
            "AssetClass": st.column_config.SelectboxColumn(
                "Asset Class", 
                options=list(st.session_state['ref_asset_classes_dict'].keys()),
                format=lambda x: st.session_state['ref_asset_classes_dict'].get(x, x),
                required=True
            ),
            "Sector_GICS": st.column_config.SelectboxColumn(
                "GICS Code", 
                options=list(st.session_state['ref_sectors_dict'].keys()),
                format=lambda x: st.session_state['ref_sectors_dict'].get(x, x),
                required=True
            ),
            "Region": st.column_config.SelectboxColumn(
                "Region", 
                options=list(st.session_state['ref_regions_dict'].keys()),
                format=lambda x: st.session_state['ref_regions_dict'].get(x, x),
                required=True
            ),
            "InstrumentType": st.column_config.SelectboxColumn(
                "Instrument Type", 
                options=list(st.session_state['ref_instr_types_dict'].keys()),
                format=lambda x: st.session_state['ref_instr_types_dict'].get(x, x),
                required=True
            ),
            # Restliche Spalten auf disabled setzen wie vorher...
            "Exchange": st.column_config.TextColumn(disabled=True),
            "Currency": st.column_config.TextColumn(disabled=True),
            "Industry": st.column_config.TextColumn("Industry (Edit)"),
            "Sector": st.column_config.TextColumn("Sector (Yahoo)", disabled=True),
            "Country": st.column_config.TextColumn("Country (Edit)"),
            "InstrumentType_Raw": st.column_config.TextColumn("Type (Yahoo)", disabled=True),
            "Vol (7d Avg)": st.column_config.NumberColumn(disabled=True, format="%d")
        }

        edited_df = st.data_editor(
            st.session_state["search_results_df"],
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key="ticker_search_editor"
        )
        
        if st.button("Daten übernehmen"):
            st.success("Daten wurden für den Import vorbereitet!")
            st.dataframe(edited_df)


