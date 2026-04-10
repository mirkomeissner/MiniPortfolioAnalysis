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

def map_yahoo_to_ref(yahoo_sector):
    mapping = {
        "Technology": "45", "Financial Services": "40", "Healthcare": "35",
        "Consumer Cyclical": "25", "Consumer Defensive": "30", "Basic Materials": "15",
        "Energy": "10", "Industrials": "20", "Communication Services": "50",
        "Utilities": "55", "Real Estate": "60"
    }
    return mapping.get(yahoo_sector, None)

def map_yahoo_to_instrument_type(quote_type, symbol_name=""):
    mapping = {
        "EQUITY": "STO", "ETF": "ETF", "MUTUALFUND": "FUN",
        "BOND": "BON", "CURRENCY": "FX", "CRYPTOCURRENCY": "CRY"
    }
    res = mapping.get(quote_type.upper(), "STO")
    if any(word in symbol_name.upper() for word in ["ZERTIFIKAT", "CERTIFICATE", "KNOCK-OUT", "WARRANT"]):
        return "CER"
    return res

def map_yahoo_to_asset_class(quote_type, symbol_name=""):
    name_up = symbol_name.upper()
    qt_up = quote_type.upper()
    if qt_up == "CURRENCY" or "MONEY MARKET" in name_up or "GELDMARKT" in name_up:
        return "LIQ"
    if qt_up == "BOND" or any(word in name_up for word in ["BOND", "RENTEN", "FIXED INCOME", "TREASURY"]):
        return "BON"
    if qt_up in ["CRYPTOCURRENCY", "COMMODITY"] or any(word in name_up for word in ["GOLD", "COMMODITY", "REIT", "REAL ESTATE"]):
        return "ALT"
    return "EQU"

# --- 2. HAUPTFUNKTION (VIEW) ---

def ticker_search_view():
    st.title("🔍 Ticker Search & Edit")
    st.write("Suchen Sie per ISIN und passen Sie die Stammdaten an.")

    # REF-Daten initialisieren
    if 'ref_data_loaded' not in st.session_state:
        with st.spinner("Lade Referenzdaten..."):
            st.session_state['db_region_map'] = get_country_mapping()
            st.session_state['ref_sectors_dict'] = get_ref_data("ref_sector")
            st.session_state['ref_regions_dict'] = get_ref_data("ref_region")
            st.session_state['ref_instr_types_dict'] = get_ref_data("ref_instrument_type")
            st.session_state['ref_asset_classes_dict'] = get_ref_data("ref_asset_class")
            st.session_state['ref_data_loaded'] = True

    # Eingabebereich
    col1, col2 = st.columns([3, 1])
    with col1:
        isin_input = st.text_input("ISIN eingeben", placeholder="z.B. US0378331005")
    with col2:
        st.write("##")
        search_button = st.button("Ticker suchen", use_container_width=True)

    # --- SUCHE LOGIK ---
    if search_button and isin_input:
        with st.spinner(f"Suche läuft für {isin_input}..."):
            try:
                search_results = yf.Search(isin_input).quotes
                if not search_results:
                    st.warning("Keine Ticker für diese ISIN gefunden.")
                else:
                    raw_data = []
                    for res in search_results:
                        symbol = res.get("symbol")
                        ticker_obj = yf.Ticker(symbol)
                        info = ticker_obj.info
                        name = info.get("longName") or res.get("longname") or "Unbekannt"
                        country = info.get("country", "Unbekannt")
                        
                        # Region Mapping
                        mapped_region = st.session_state['db_region_map'].get(country, "GLO")
                        if any(word in name.upper() for word in ["WORLD", "GLOBAL", "ALL COUNTRY"]):
                            mapped_region = "GLO"
                        elif "DEVELOPED" in name.upper():
                            mapped_region = "DEV"
                        
                        yahoo_sector = info.get("sector")
                        raw_type = res.get("quoteType") or info.get("quoteType") or "EQUITY"
                        
                        row = {
                            "Ticker": symbol,
                            "Name": name,
                            "Exchange": info.get("exchange"),
                            "Currency": info.get("currency"),
                            "AssetClass": map_yahoo_to_asset_class(raw_type, name),
                            "Industry": info.get("industry"),
                            "Sector": yahoo_sector,
                            "Sector_GICS": map_yahoo_to_ref(yahoo_sector),
                            "Country": country,
                            "Region": mapped_region,
                            "InstrumentType_Raw": raw_type,
                            "InstrumentType": map_yahoo_to_instrument_type(raw_type, name),
                            "Vol (7d Avg)": 0
                        }

                        hist = ticker_obj.history(period="7d")
                        if not hist.empty:
                            row["Vol (7d Avg)"] = int(hist['Volume'].mean())
                        
                        raw_data.append(row)
                    
                    st.session_state["search_results_df"] = pd.DataFrame(raw_data)

            except Exception as e:
                st.error(f"Suche fehlgeschlagen: {e}")

    # --- EDITABLE TABLE AREA ---
    if "search_results_df" in st.session_state:
        st.subheader("Stammdaten verfeinern")
        
        # Sicherstellen, dass wir Listen für die Optionen haben
        # Falls der Dictionary-Key nicht existiert, wird eine leere Liste [] als Fallback genutzt
        column_config = {
            "Ticker": st.column_config.TextColumn(disabled=True),
            "Name": st.column_config.TextColumn(disabled=True),
            "AssetClass": st.column_config.SelectboxColumn(
                "Asset Class", 
                options=list(st.session_state.get('ref_asset_classes_dict', {}).keys()),
                format=lambda x: st.session_state.get('ref_asset_classes_dict', {}).get(x, x),
                required=True
            ),
            "Sector_GICS": st.column_config.SelectboxColumn(
                "GICS Code", 
                options=list(st.session_state.get('ref_sectors_dict', {}).keys()),
                format=lambda x: st.session_state.get('ref_sectors_dict', {}).get(x, x),
                required=True
            ),
            "Region": st.column_config.SelectboxColumn(
                "Region", 
                options=list(st.session_state.get('ref_regions_dict', {}).keys()),
                format=lambda x: st.session_state.get('ref_regions_dict', {}).get(x, x),
                required=True
            ),
            "InstrumentType": st.column_config.SelectboxColumn(
                "Instrument Type", 
                options=list(st.session_state.get('ref_instr_types_dict', {}).keys()),
                format=lambda x: st.session_state.get('ref_instr_types_dict', {}).get(x, x),
                required=True
            ),
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
            key="ticker_search_editor_v4"
        )
        
        if st.button("Daten übernehmen"):
            st.success("Daten wurden für den Import vorbereitet!")
            st.dataframe(edited_df)

