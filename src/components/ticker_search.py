import streamlit as st
import yfinance as yf
import pandas as pd
from src.database import supabase

# --- 1. HILFSFUNKTIONEN ---

def get_ref_data(table_name):
    try:
        response = supabase.table(table_name).select("code, label").execute()
        if not response.data:
            return {}
        return {item['code']: f"{item['code']} ({item['label']})" for item in response.data}
    except Exception as e:
        st.error(f"Fehler beim Laden von {table_name}: {e}")
        return {}

def get_country_mapping():
    try:
        response = supabase.table("country_region_mapping").select("country, region_code").execute()
        return {item['country']: item['region_code'] for item in response.data}
    except Exception as e:
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


# --- 2. HAUPTFUNKTION ---

def ticker_search_view():
    st.title("🔍 Ticker Search & Edit")

    # Initialisierung der REF-Daten
    if 'ref_data_loaded' not in st.session_state:
        with st.spinner("Lade Referenzdaten..."):
            st.session_state['db_region_map'] = get_country_mapping()
            st.session_state['ref_sectors_dict'] = get_ref_data("ref_sector")
            st.session_state['ref_regions_dict'] = get_ref_data("ref_region")
            st.session_state['ref_instr_types_dict'] = get_ref_data("ref_instrument_type")
            st.session_state['ref_asset_classes_dict'] = get_ref_data("ref_asset_class")
            st.session_state['ref_data_loaded'] = True

    # Sucheingabe
    isin_input = st.text_input("ISIN eingeben", placeholder="z.B. US0378331005")
    search_button = st.button("Ticker suchen")

    if search_button and isin_input:
        with st.spinner("Suche läuft..."):
            try:
                search_results = yf.Search(isin_input).quotes
                if not search_results:
                    st.warning("Keine Ergebnisse.")
                else:
                    raw_data = []
                    for res in search_results:
                        symbol = res.get("symbol")
                        t = yf.Ticker(symbol)
                        info = t.info
                        name = info.get("longName") or res.get("longname") or "Unbekannt"
                        raw_type = res.get("quoteType") or info.get("quoteType") or "EQUITY"
                        
                        raw_data.append({
                            "Ticker": symbol,
                            "Name": name,
                            "Exchange": info.get("exchange"),
                            "Currency": info.get("currency"),
                            "AssetClass": map_yahoo_to_asset_class(raw_type, name),
                            "Industry": info.get("industry"),
                            "Sector": info.get("sector"),
                            "Sector_GICS": map_yahoo_to_ref(info.get("sector")),
                            "Country": info.get("country", "Unknown"),
                            "Region": st.session_state['db_region_map'].get(info.get("country"), "GLO"),
                            "InstrumentType_Raw": raw_type,
                            "InstrumentType": map_yahoo_to_instrument_type(raw_type, name),
                            "Vol (7d Avg)": int(t.history(period="7d")['Volume'].mean()) if not t.history(period="7d").empty else 0
                        })
                    st.session_state["search_results_df"] = pd.DataFrame(raw_data)
            except Exception as e:
                st.error(f"Suche fehlgeschlagen: {e}")

    # --- TABELLE ---
    if "search_results_df" in st.session_state:
        # SICHERHEITS-CHECK: Fallback-Listen falls Dictionaries leer sind
        # Das verhindert den TypeError!
        opt_asset = list(st.session_state.get('ref_asset_classes_dict', {}).keys()) or ["EQU", "BON", "LIQ", "ALT"]
        opt_gics = list(st.session_state.get('ref_sectors_dict', {}).keys()) or ["10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60"]
        opt_region = list(st.session_state.get('ref_regions_dict', {}).keys()) or ["GLO", "DEV", "EM", "EUR", "USA"]
        opt_type = list(st.session_state.get('ref_instr_types_dict', {}).keys()) or ["STO", "ETF", "FUN", "BON", "FX", "CRY", "CER"]

        column_config = {
            "Ticker": st.column_config.TextColumn(disabled=True),
            "Name": st.column_config.TextColumn(disabled=True),
            "AssetClass": st.column_config.SelectboxColumn(
                "Asset Class", 
                options=opt_asset,
                format=lambda x: st.session_state.get('ref_asset_classes_dict', {}).get(x, x)
            ),
            "Sector_GICS": st.column_config.SelectboxColumn(
                "GICS", 
                options=opt_gics,
                format=lambda x: st.session_state.get('ref_sectors_dict', {}).get(x, x)
            ),
            "Region": st.column_config.SelectboxColumn(
                "Region", 
                options=opt_region,
                format=lambda x: st.session_state.get('ref_regions_dict', {}).get(x, x)
            ),
            "InstrumentType": st.column_config.SelectboxColumn(
                "Type", 
                options=opt_type,
                format=lambda x: st.session_state.get('ref_instr_types_dict', {}).get(x, x)
            ),
            "Exchange": st.column_config.TextColumn(disabled=True),
            "Currency": st.column_config.TextColumn(disabled=True),
            "Industry": st.column_config.TextColumn("Industry"),
            "Sector": st.column_config.TextColumn("Yahoo Sector", disabled=True),
            "Country": st.column_config.TextColumn("Country"),
            "InstrumentType_Raw": st.column_config.TextColumn("Yahoo Type", disabled=True),
            "Vol (7d Avg)": st.column_config.NumberColumn(disabled=True, format="%d")
        }

        st.data_editor(
            st.session_state["search_results_df"],
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key="final_editor"
        )






