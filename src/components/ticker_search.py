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

    # Flexible search input
    search_input = st.text_input("Enter ISIN, Ticker or Name", placeholder="e.g. AU000000DRO2 or Apple")
    
    if st.button("Search Asset") and search_input:
        with st.spinner("Fetching data from Yahoo Finance..."):
            try:
                search_results = yf.Search(search_input).quotes
                if not search_results:
                    st.warning("No results found.")
                else:
                    raw_data = []
                    input_is_isin = len(search_input) == 12 and search_input[0:2].isalpha()
                    
                    for res in search_results:
                        symbol = res.get("symbol")
                        t = yf.Ticker(symbol)
                        info = t.info
                        
                        # --- CLEAN ISIN LOGIC ---
                        found_isin = ""
                        if input_is_isin:
                            found_isin = search_input.upper()
                        else:
                            y_isin = res.get('isin') or info.get('isin')
                            if y_isin and y_isin != symbol and y_isin != '-':
                                found_isin = y_isin
                        
                        # --- CURRENCY & PRICE ---
                        currency = info.get("currency", "Unknown")
                        current_price = info.get("currentPrice") or info.get("navPrice") or info.get("regularMarketPrice")
                        
                        # --- METADATA ---
                        name = info.get("longName") or res.get("longname") or "Unknown"
                        raw_type = res.get("quoteType") or info.get("quoteType") or "EQUITY"
                        raw_sector = info.get("sector", "Unknown")
                        
                        raw_data.append({
                            "ISIN": found_isin,
                            "Ticker": symbol,
                            "Name": name,
                            "Price": current_price,
                            "Currency": currency,
                            "Exchange": info.get("exchange", "Unknown"),
                            "Volume (Shares)": get_average_volume_7d(t),
                            "Industry": info.get("industry", "Unknown"),
                            "Sector Raw": raw_sector, # Back in the data
                            "Sector_GICS": next((s for s in st.session_state['opt_gics'] if s.startswith(str(map_yahoo_to_ref(raw_sector)))) , "Unknown"),
                            "Country": info.get("country", "Unknown"),
                            "Region": next((s for s in st.session_state['opt_region'] if s.startswith(st.session_state['db_region_map'].get(info.get("country"), "GLO"))), "GLO"),
                            "Type Raw": raw_type, # Back in the data
                            "InstrumentType": next((s for s in st.session_state['opt_type'] if s.startswith(map_yahoo_to_instrument_type(raw_type, name))), "STO"),
                            "AssetClass": next((s for s in st.session_state['opt_asset'] if s.startswith(map_yahoo_to_asset_class(raw_type, name))), "EQU")
                        })
                    st.session_state["search_results_df"] = pd.DataFrame(raw_data)
            except Exception as e:
                st.error(f"Search failed: {e}")

    if "search_results_df" in st.session_state:
        df = st.session_state["search_results_df"]
        st.subheader("1. Review & Edit Data")
        
        # Consistent column order: Raw columns placed before editable ones
        if "Volume (Shares)" in df.columns:
            df = df.sort_values(by="Volume (Shares)", ascending=False)
            cols = ["Volume (Shares)", "Ticker", "ISIN", "Price", "Currency", "Sector Raw", "Sector_GICS", "Type Raw", "InstrumentType"]
            remaining_cols = [c for c in df.columns if c not in cols]
            df = df[cols + remaining_cols]

        column_config = {
            "ISIN": st.column_config.TextColumn("ISIN (Edit if empty)", disabled=False),
            "Ticker": st.column_config.TextColumn("Ticker", disabled=True),
            "Price": st.column_config.NumberColumn("Price", format="%.2f", disabled=True),
            "Currency": st.column_config.TextColumn("Curr", disabled=True),
            "Volume (Shares)": st.column_config.NumberColumn("Vol (7d Avg)", disabled=True),
            "Sector Raw": st.column_config.TextColumn("Sector Raw", disabled=True),
            "Sector_GICS": st.column_config.SelectboxColumn("Sector GICS", options=st.session_state['opt_gics'], required=True),
            "Type Raw": st.column_config.TextColumn("Type Raw", disabled=True),
            "InstrumentType": st.column_config.SelectboxColumn("Type", options=st.session_state['opt_type'], required=True),
            "Region": st.column_config.SelectboxColumn("Region", options=st.session_state['opt_region'], required=True),
            "AssetClass": st.column_config.SelectboxColumn("Asset Class", options=st.session_state['opt_asset'], required=True)
        }

        edited_df = st.data_editor(df, column_config=column_config, use_container_width=True, hide_index=True, key="ticker_editor")

        st.markdown("---")
        st.subheader("2. Save Selection")
        selected_ticker = st.selectbox("Select ticker to save:", options=edited_df["Ticker"].tolist())

        if selected_ticker and st.button("Save to Database", type="primary"):
            row = edited_df[edited_df["Ticker"] == selected_ticker].iloc[0]
            if not row["ISIN"] or len(row["ISIN"]) < 5:
                st.error("Please enter a valid ISIN in the table above before saving.")
            else:
                handle_save_request(row, row["ISIN"])


    


    


