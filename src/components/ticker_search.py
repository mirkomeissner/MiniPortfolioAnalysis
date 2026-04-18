import streamlit as st
import yfinance as yf
import pandas as pd
from src.utils import ensure_reference_data, extract_code
from src.database import save_asset_static_data, get_ref_options, get_country_region_map

# --- 0. HELPER FUNCTIONS ---

def get_average_volume_7d(ticker):
    """Return the average trading volume for the last 7 trading days."""
    try:
        history = ticker.history(period="14d", interval="1d")
        if history is None or history.empty:
            return None
        volumes = history.get("Volume")
        if volumes is None or volumes.dropna().empty:
            return None
        last7 = volumes.dropna().tail(7)
        return int(last7.mean()) if not last7.empty else None
    except Exception:
        return None

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
    # Wir nutzen hier die extract_code Funktion aus deinen utils
    # um sicherzustellen, dass nur 'EQU' statt 'EQU (Equity)' gespeichert wird.
    # Wir ziehen die UUID des Users, da dein neues Schema UUID erwartet
    current_user_id = st.session_state.get('user_id')
    
    asset_entry = {
        "isin": isin,
        "name": row["Name"],
        "currency": row["Currency"],
        "ticker": row["Ticker"],
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

    # Flexible search input for ISIN, Ticker, or Name
    search_input = st.text_input("Enter ISIN, Ticker or Name", placeholder="e.g. Apple, AAPL or US0378331005")
    
    if st.button("Search Asset") and search_input:
        with st.spinner("Fetching data from Yahoo Finance..."):
            try:
                search_results = yf.Search(search_input).quotes
                if not search_results:
                    st.warning("No results found for this search term.")
                else:
                    raw_data = []
                    for res in search_results:
                        symbol = res.get("symbol")
                        # Preserve actual ISIN or fallback to symbol
                        found_isin = res.get("isin") or symbol
                        
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

                        avg_vol_7d = get_average_volume_7d(t)

                        raw_data.append({
                            "ISIN": found_isin,
                            "Volume 7 days": avg_vol_7d,
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
        
        # Updated column ordering: Volume first, then Ticker, then ISIN
        if "Volume 7 days" in df.columns:
            df = df.sort_values(by="Volume 7 days", ascending=False, na_position="last")
            ordered_cols = ["Volume 7 days", "Ticker", "ISIN"] + [col for col in df.columns if col not in ["Volume 7 days", "Ticker", "ISIN"]]
            df = df[ordered_cols]

        column_config = {
            "ISIN": st.column_config.TextColumn("ISIN", disabled=True),
            "Volume 7 days": st.column_config.NumberColumn("Volume 7 days", disabled=True),
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

        edited_df = st.data_editor(
            df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key="ticker_editor"
        )

        st.markdown("---")
        st.subheader("2. Select Ticker for Import")
        
        ticker_options = edited_df["Ticker"].tolist()
        selected_ticker = st.selectbox("Which ticker would you like to save?", options=ticker_options)

        if selected_ticker:
            selected_row = edited_df[edited_df["Ticker"] == selected_ticker].iloc[0]
            
            if st.button("Save to Database", type="primary", use_container_width=True):
                # Pass the validated ISIN from the selected row
                handle_save_request(selected_row, selected_row["ISIN"])



