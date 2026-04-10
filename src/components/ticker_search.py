import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from src.database import supabase

def get_ref_options(table_name, column_name="code"):
    """Helper to fetch valid options for dropdowns from REF tables."""
    try:
        response = supabase.table(table_name).select(column_name).execute()
        return [item[column_name] for item in response.data]
    except Exception as e:
        st.error(f"Error loading {table_name}: {e}")
        return []

def get_country_mapping():
    """Fetch the mapping from Supabase and return as a dictionary."""
    try:
        response = supabase.table("country_region_mapping").select("country, region_code").execute()
        return {item['country']: item['region_code'] for item in response.data}
    except Exception as e:
        st.error(f"Error loading region mapping: {e}")
        return {}

def map_yahoo_to_ref(yahoo_sector):
    mapping = {
        "Technology": "45",
        "Financial Services": "40",
        "Healthcare": "35",
        "Consumer Cyclical": "25",
        "Consumer Defensive": "30",
        "Basic Materials": "15",
        "Energy": "10",
        "Industrials": "20",
        "Communication Services": "50",
        "Utilities": "55",
        "Real Estate": "60"
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

def ticker_search_view():
    st.title("🔍 Ticker Search & Edit")
    st.write("Search via ISIN and refine the metadata before saving.")

    # 1. Load all required mappings and REF-data into session state
    if 'ref_data_loaded' not in st.session_state:
        st.session_state['db_region_map'] = get_country_mapping()
        st.session_state['ref_sectors'] = get_ref_options("ref_sector")
        st.session_state['ref_regions'] = get_ref_options("ref_region")
        st.session_state['ref_instr_types'] = get_ref_options("ref_instrument_type")
        st.session_state['ref_data_loaded'] = True

    # Input Area
    col1, col2 = st.columns([3, 1])
    with col1:
        isin_input = st.text_input("Enter ISIN", placeholder="e.g. US0378331005")
    with col2:
        st.write("##")
        search_button = st.button("Search Ticker", use_container_width=True)

    if search_button and isin_input:
        with st.spinner(f"Searching for {isin_input}..."):
            try:
                search_results = yf.Search(isin_input).quotes
                if not search_results:
                    st.warning("No tickers found for this ISIN.")
                else:
                    raw_data = []
                    for res in search_results:
                        symbol = res.get("symbol")
                        ticker_obj = yf.Ticker(symbol)
                        info = ticker_obj.info
                        name = info.get("longName") or res.get("longname") or ""
                        country = info.get("country", "Unknown")
                        
                        # Region Logic
                        if any(word in name.upper() for word in ["WORLD", "GLOBAL", "ALL COUNTRY"]):
                            mapped_region = "GLO"
                        elif "DEVELOPED" in name.upper():
                            mapped_region = "DEV"
                        else:
                            mapped_region = st.session_state['db_region_map'].get(country, "GLO")

                        # GICS and Instrument Type
                        yahoo_sector = info.get("sector")
                        gics_code = map_yahoo_to_ref(yahoo_sector)
                        raw_type = res.get("quoteType") or info.get("quoteType")
                        instr_type = map_yahoo_to_instrument_type(raw_type, name)

                        # Volume
                        hist = ticker_obj.history(period="7d")
                        avg_volume = hist['Volume'].mean() if not hist.empty else 0
                        
                        raw_data.append({
                            "Ticker": symbol,
                            "Name": name,
                            "InstrumentType": instr_type,
                            "Sector_GICS": gics_code,
                            "Industry": info.get("industry"),
                            "Country": country,
                            "Region": mapped_region,
                            "Currency": info.get("currency"),
                            "Exchange": info.get("exchange"),
                            "Vol (7d Avg)": int(avg_volume)
                        })
                    
                    st.session_state["search_results_df"] = pd.DataFrame(raw_data)

            except Exception as e:
                st.error(f"Search failed: {e}")

    # --- EDITABLE TABLE AREA ---
    if "search_results_df" in st.session_state:
        st.subheader("Refine Metadata")
        st.info("The fields below are pre-filled based on our logic. You can edit them using the dropdowns.")
        
        # Configure the columns for editing
        column_config = {
            "Ticker": st.column_config.TextColumn(disabled=True),
            "Name": st.column_config.TextColumn(disabled=True),
            "InstrumentType": st.column_config.SelectboxColumn(
                "Type", options=st.session_state['ref_instr_types'], required=True
            ),
            "Sector_GICS": st.column_config.SelectboxColumn(
                "GICS Code", options=st.session_state['ref_sectors'], required=True
            ),
            "Industry": st.column_config.TextColumn("Industry"),
            "Country": st.column_config.TextColumn("Country"),
            "Region": st.column_config.SelectboxColumn(
                "Region", options=st.session_state['ref_regions'], required=True
            ),
            "Exchange": st.column_config.TextColumn(disabled=True),
            "Currency": st.column_config.TextColumn(disabled=True),
            "Vol (7d Avg)": st.column_config.NumberColumn(disabled=True, format="%d")
        }

        edited_df = st.data_editor(
            st.session_state["search_results_df"],
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key="ticker_editor"
        )
        
        # Action Button (Placeholder for saving)
        if st.button("Accept Data"):
            st.success("Data refined! Ready to be saved to the database.")
            st.write(edited_df) # Hier könntest du den Insert in Assets machen

