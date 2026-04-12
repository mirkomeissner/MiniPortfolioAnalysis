import streamlit as st
import yfinance as yf
import pandas as pd
from src.utils import ensure_reference_data, extract_code, get_option_index
from src.database import save_asset_static_data, get_ref_options, get_country_region_map

# --- 1. MAPPING (Yahoo Finance -> DB-Standard) ---

def map_yahoo_to_ref(yahoo_sector):
    """Mapping Yahoo Sectors to GICS Codes."""
    mapping = {
        "Technology": "45", "Financial Services": "40", "Healthcare": "35",
        "Consumer Cyclical": "25", "Consumer Defensive": "30", "Basic Materials": "15",
        "Energy": "10", "Industrials": "20", "Communication Services": "50",
        "Utilities": "55", "Real Estate": "60"
    }
    return mapping.get(yahoo_sector)

def map_yahoo_to_instrument_type(quote_type, symbol_name=""):
    """Determine Instrumententype based on Yahoo Meta-Data."""
    mapping = {
        "EQUITY": "STO", "ETF": "ETF", "MUTUALFUND": "FUN", 
        "BOND": "BON", "CURRENCY": "FX", "CRYPTOCURRENCY": "CRY"
    }
    res = mapping.get(str(quote_type).upper(), "STO")
    # Sonderlogik für Zertifikate
    if any(word in str(symbol_name).upper() for word in ["ZERTIFIKAT", "CERTIFICATE", "WARRANT"]):
        return "CER"
    return res

def map_yahoo_to_asset_class(quote_type, symbol_name=""):
    """Mapping Yahoo Types to Asset Classes."""
    name_up = str(symbol_name).upper()
    qt_up = str(quote_type).upper()
    if qt_up == "CURRENCY" or "MONEY MARKET" in name_up: return "LIQ"
    if qt_up == "BOND" or any(word in name_up for word in ["BOND", "RENTEN", "TREASURY"]): return "BON"
    if qt_up in ["CRYPTOCURRENCY", "COMMODITY"] or any(word in name_up for word in ["GOLD", "REIT"]): return "ALT"
    return "EQU"

# --- 2. helper functions for UI ---

def handle_save_request(row, isin):
    def clean_code(val):
        return val.split(" (")[0] if val and " (" in str(val) else val

    asset_entry = {
        "isin": isin,
        "name": row["Name"],
        "currency": row["Currency"],
        "ticker": row["Ticker"],
        "price_source": "YFN",
        "instrument_type": clean_code(row["InstrumentType"]),
        "asset_class_code": clean_code(row["AssetClass"]),
        "region_code": clean_code(row["Region"]),
        "sector_code": clean_code(row["Sector_GICS"]),
        "industry": row["Industry"],
        "country": row["Country"],
        "created_by": st.session_state.get('user_name', 'System')
    }

    try:
        save_asset_static_data(asset_entry)
        st.success(f"✅ {row['Ticker']} saved successfully!")
        st.cache_data.clear()
        st.session_state["view"] = "list" 
        st.rerun() 
    except Exception as e:
        st.error(f"Error saving data: {e}")

def render_ticker_search():
    """
    Provides a search interface for Yahoo Finance tickers and 
    allows adding them to the local asset database.
    """
    st.header("Search & Add Ticker")

    # 1. Centralized loading of reference data (Sectors, Asset Classes, etc.)
    ensure_reference_data()

    # 2. Search UI
    with st.expander("Search Parameters", expanded=True):
        search_col, btn_col = st.columns([3, 1])
        query = search_col.text_input("Company Name or Symbol", placeholder="e.g. Microsoft or MSFT")
        
        if btn_col.button("Search Ticker", use_container_width=True):
            if query:
                # Assuming search_yahoo_finance is a function in your logic
                # st.session_state['search_results'] = search_yahoo_finance(query)
                st.info(f"Searching for '{query}'...") 
            else:
                st.warning("Please enter a search term.")

    # 3. Add to Database Form (Simplified Example)
    st.divider()
    st.subheader("Add Asset Details")
    
    with st.form("add_ticker_form"):
        col1, col2 = st.columns(2)
        
        # Use helper 'get_option_index' to maintain selection on rerun if needed
        selected_class = col1.selectbox(
            "Asset Class", 
            st.session_state['opt_asset']
        )
        
        selected_sector = col2.selectbox(
            "GICS Sector", 
            st.session_state['opt_gics']
        )

        if st.form_submit_button("Save to Portfolio"):
            # Use helper 'extract_code' to get 'EQU' from 'EQU (Equity)'
            asset_code = extract_code(selected_class)
            sector_code = extract_code(selected_sector)
            
            st.success(f"Saved with Codes: {asset_code} / {sector_code}")




def ticker_search_view():
    st.subheader("🔍 Search New Asset via ISIN")

    if 'ref_data_loaded' not in st.session_state:
        with st.spinner("Loading reference data..."):
            st.session_state['db_region_map'] = get_country_region_map()
            st.session_state['opt_asset'] = get_ref_options("ref_asset_class")
            st.session_state['opt_gics'] = get_ref_options("ref_sector")
            st.session_state['opt_region'] = get_ref_options("ref_region")
            st.session_state['opt_type'] = get_ref_options("ref_instrument_type")
            st.session_state['ref_data_loaded'] = True

    isin_input = st.text_input("Enter ISIN", placeholder="e.g. US0378331005")
    
    if st.button("Search Ticker") and isin_input:
        with st.spinner("Fetching data from Yahoo Finance..."):
            try:
                search_results = yf.Search(isin_input).quotes
                if not search_results:
                    st.warning("No results found for this ISIN.")
                else:
                    raw_data = []
                    for res in search_results:
                        symbol = res.get("symbol")
                        t = yf.Ticker(symbol)
                        info = t.info
                        
                        name = info.get("longName") or res.get("longname") or "Unknown"
                        raw_type = res.get("quoteType") or info.get("quoteType") or "EQUITY"
                        raw_sector = info.get("sector", "Unknown")
                        
                        # Mapping to Internal Codes
                        a_code = map_yahoo_to_asset_class(raw_type, name)
                        asset_val = next((s for s in st.session_state['opt_asset'] if s.startswith(a_code)), a_code)
                        
                        g_code = map_yahoo_to_ref(raw_sector)
                        gics_val = next((s for s in st.session_state['opt_gics'] if s.startswith(str(g_code))), str(g_code))
                        
                        r_code = st.session_state['db_region_map'].get(info.get("country"), "GLO")
                        reg_val = next((s for s in st.session_state['opt_region'] if s.startswith(r_code)), r_code)
                        
                        i_code = map_yahoo_to_instrument_type(raw_type, name)
                        type_val = next((s for s in st.session_state['opt_type'] if s.startswith(i_code)), i_code)

                        raw_data.append({
                            "Ticker": symbol,
                            "Name": name,
                            "Exchange": info.get("exchange", "Unknown"),
                            "Currency": info.get("currency", "Unknown"),
                            "Industry": info.get("industry", "Unknown"),
                            "Sector Raw": raw_sector,
                            "Sector_GICS": gics_val,
                            "Country": info.get("country", "Unknown"),
                            "Region": reg_val,
                            "Type Raw": raw_type,
                            "InstrumentType": type_val,
                            "AssetClass": asset_val
                        })
                    st.session_state["search_results_df"] = pd.DataFrame(raw_data)
            except Exception as e:
                st.error(f"Search failed: {e}")

    if "search_results_df" in st.session_state:
        df = st.session_state["search_results_df"]
        st.subheader("1. Review & Edit Data")
        
        # --- COLUMN CONFIGURATION ---
        column_config = {
            "Ticker": st.column_config.TextColumn("Ticker", disabled=True),
            "Name": st.column_config.TextColumn("Name"),
            "Exchange": st.column_config.TextColumn("Exchange"),
            "Currency": st.column_config.TextColumn("Currency"),
            "Industry": st.column_config.TextColumn("Industry"),
            "Sector Raw": st.column_config.TextColumn("Sector Raw", disabled=True),
            "Sector_GICS": st.column_config.SelectboxColumn("Sector GICS", options=st.session_state['opt_gics'], required=True),
            "Country": st.column_config.TextColumn("Country"),
            "Region": st.column_config.SelectboxColumn("Region", options=st.session_state['opt_region'], required=True),
            "Type Raw": st.column_config.TextColumn("Type Raw", disabled=True),
            "InstrumentType": st.column_config.SelectboxColumn("Instrument Type", options=st.session_state['opt_type'], required=True),
            "AssetClass": st.column_config.SelectboxColumn("Asset Class", options=st.session_state['opt_asset'], required=True)
        }

        # Display the data editor
        edited_df = st.data_editor(
            df, 
            column_config=column_config, 
            use_container_width=True, 
            hide_index=True, 
            key="ticker_editor"
        )

        st.markdown("---")
        st.subheader("2. Select Ticker for Import")
        
        # User selection based on edited data
        ticker_options = edited_df["Ticker"].tolist()
        selected_ticker = st.selectbox("Which ticker would you like to save?", options=ticker_options)

        if selected_ticker:
            # We pull the row from the EDITED dataframe so manual changes are preserved
            selected_row = edited_df[edited_df["Ticker"] == selected_ticker].iloc[0]
            
            if st.button("Save to Database", type="primary", use_container_width=True):
                handle_save_request(selected_row, isin_input)

