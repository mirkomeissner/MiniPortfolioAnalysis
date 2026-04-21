import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from src.database import (
    get_all_assets_with_labels, 
    update_asset_static_data, 
    get_ref_options
)
from src.utils import (
    extract_code, 
    get_option_index, 
    ensure_reference_data, 
    apply_advanced_filters
)
from .ticker_search import ticker_search_view

# --- HELPER FUNCTIONS FROM ticker_search.py ---

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

def handle_reload_save(row, isin):
    updated_payload = {
        "name": row["Name"],
        "ticker": row["Ticker"],
        "currency": row["Currency"],
        "asset_class_code": extract_code(row["AssetClass"]),
        "region_code": extract_code(row["Region"]),
        "sector_code": extract_code(row["Sector_GICS"]),
        "instrument_type_code": extract_code(row["InstrumentType"]),
        "price_source_code": "YFN",
        "industry": row["Industry"],
        "country": row["Country"],
        "updated_at": datetime.now().isoformat(),
        "updated_by": st.session_state.get("user_name", "System")
    }
    update_asset_static_data(isin, updated_payload)
    st.success("Asset updated with reloaded data!")
    st.cache_data.clear()
    if "reload_results_df" in st.session_state:
        del st.session_state["reload_results_df"]
    st.session_state["view"] = "list"
    st.rerun()

def asset_table_view():
    # --- VIEW ROUTING ---
    current_view = st.session_state.get("view", "list")

    if current_view == "search":
        if st.button("⬅ Back to List"):
            st.session_state["view"] = "list"
            st.rerun()
        ticker_search_view()

    elif current_view == "edit":
        render_edit_view()

    else:
        render_list_view()



def render_list_view():
    st.title("Asset Static Data")
    
    # 1. Navigation
    if st.button("➕ New ISIN"):
        st.session_state["view"] = "search"
        st.rerun()

    # 2. Data Loading & Filtering
    data = get_all_assets_with_labels()
    if not data:
        st.info("No records found.")
        return

    df = pd.DataFrame(data)

    # Filtering logic (remains the same)
    def closed_on_logic(df_in, widget_col, index, prefix):
        selection = widget_col.selectbox(
            f"Criteria {index}", 
            ["Is Null (Active Assets)", "Is Not Null (Closed Assets)"], 
            key=f"{prefix}_closed_val_{index}"
        )
        return df_in["Closed On"].isna() if selection == "Is Null (Active Assets)" else df_in["Closed On"].notna()

    filtered_df = apply_advanced_filters(df, session_prefix="asset_management", custom_filter_logic={"Closed On": closed_on_logic})

    # 3. Column Order (as requested)
    column_order = [
        "ISIN", "Name", "Ticker", "Currency", "Type", 
        "Asset Class", "Region", "Sector", "Industry", 
        "Country", "Price Source", "Closed On", 
        "Created At", "Created By", "Updated At", "Updated By"
    ]
    existing_cols = [c for c in column_order if c in filtered_df.columns]
    display_df = filtered_df[existing_cols]

    # --- VISUAL FEEDBACK ---
    st.info(f"Displaying {len(display_df)} assets. **Select a row using the button on the left to edit.**")

    # 4. DATA TABLE (Native Selection - No Page Reload)
    # This is the ONLY way to stay in the same session without losing login.
    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",           # Trigger rerun within the SAME session
        selection_mode="single-row", # Enables the radio-button on the left
    )

    # 5. SELECTION LOGIC
    # This triggers instantly without opening new tabs or losing login status
    if event.selection.rows:
        selected_index = event.selection.rows[0]
        st.session_state["edit_isin"] = display_df.iloc[selected_index]["ISIN"]
        st.session_state["view"] = "edit"
        st.rerun()


def render_edit_view():
    isin = st.session_state.get("edit_isin")
    st.subheader(f"Edit Asset: {isin}")
    
    if st.button("⬅ Cancel"):
        st.session_state["view"] = "list"
        st.rerun()

    # 1. Load current data
    all_data = get_all_assets_with_labels()
    asset = next((item for item in all_data if item["ISIN"] == isin), None)

    if not asset:
        st.error("Asset not found.")
        return

    # --- CLOSE / REOPEN LOGIC ---
    st.write("---")
    closed_val = asset.get("Closed On")
    
    if closed_val is None:
        if st.button("🔒 Close Asset", help="Set the closing date to today", use_container_width=True):
            update_asset_static_data(isin, {
                "closed_on": datetime.now().date().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "updated_by": st.session_state.get("user_name", "System")
            })
            st.success("Asset closed.")
            st.cache_data.clear()
            st.session_state["view"] = "list"
            st.rerun()
    else:
        st.warning(f"This asset was closed on {closed_val}")
        if st.button("🔓 Reopen Asset", help="Clear the closing date", use_container_width=True):
            update_asset_static_data(isin, {
                "closed_on": None,
                "updated_at": datetime.now().isoformat(),
                "updated_by": st.session_state.get("user_name", "System")
            })
            st.success("Asset reopened.")
            st.cache_data.clear()
            st.session_state["view"] = "list"
            st.rerun()
    st.write("---")

    # --- RELOAD FROM YAHOO FINANCE ---
    if st.button("Reload from Yahoo Finance"):
        with st.spinner("Fetching data from Yahoo Finance..."):
            try:
                search_results = yf.Search(isin).quotes
                if not search_results:
                    st.error("No data found for this ISIN.")
                else:
                    raw_data = []
                    for res in search_results:
                        symbol = res.get("symbol")
                        t = yf.Ticker(symbol)
                        info = t.info
                        
                        found_isin = isin.upper()
                        currency = info.get("currency", "Unknown")
                        current_price = info.get("currentPrice") or info.get("navPrice") or info.get("regularMarketPrice")
                        name = info.get("longName") or res.get("longname") or "Unknown"
                        raw_type = res.get("quoteType") or info.get("quoteType") or "EQUITY"
                        raw_sector = info.get("sector", "Unknown")
                        
                        raw_data.append({
                            "Volume (avg 7d)": get_average_volume_7d(t),
                            "ISIN": found_isin,
                            "Ticker": symbol,
                            "Name": name,
                            "Price": current_price,
                            "Currency": currency,
                            "Exchange": info.get("exchange", "Unknown"),
                            "Industry": info.get("industry", "Unknown"),
                            "Sector Raw": raw_sector,
                            "Sector_GICS": next((s for s in st.session_state['opt_gics'] if s.startswith(str(map_yahoo_to_ref(raw_sector)))), "Unknown"),
                            "Country": info.get("country", "Unknown"),
                            "Region": next((s for s in st.session_state['opt_region'] if s.startswith(st.session_state['db_region_map'].get(info.get("country"), "GLO"))), "GLO"),
                            "Type Raw": raw_type,
                            "InstrumentType": next((s for s in st.session_state['opt_type'] if s.startswith(map_yahoo_to_instrument_type(raw_type, name))), "STO"),
                            "AssetClass": next((s for s in st.session_state['opt_asset'] if s.startswith(map_yahoo_to_asset_class(raw_type, name))), "EQU")
                        })
                    df = pd.DataFrame(raw_data)
                    if "Volume (avg 7d)" in df.columns and not df.empty:
                        df = df.sort_values(by="Volume (avg 7d)", ascending=False)
                    st.session_state["reload_results_df"] = df
                    st.rerun()
            except Exception as e:
                st.error(f"Failed to fetch data: {e}")

    if "reload_results_df" in st.session_state:
        df = st.session_state["reload_results_df"]
        st.subheader("1. Review & Edit Reloaded Data")
        st.info("Review the data fetched from Yahoo Finance. Edit if necessary.")
        
        column_config = {
            "ISIN": st.column_config.TextColumn("ISIN", disabled=True),
            "Ticker": st.column_config.TextColumn("Ticker", disabled=True),
            "Price": st.column_config.NumberColumn("Price", format="%.2f", disabled=True),
            "Currency": st.column_config.TextColumn("Curr", disabled=True),
            "Volume (avg 7d)": st.column_config.NumberColumn("Vol (7d Avg)", disabled=True),
            "Sector Raw": st.column_config.TextColumn("Sector Raw", disabled=True),
            "Sector_GICS": st.column_config.SelectboxColumn("Sector GICS", options=st.session_state['opt_gics'], required=True),
            "Type Raw": st.column_config.TextColumn("Type Raw", disabled=True),
            "InstrumentType": st.column_config.SelectboxColumn("Type", options=st.session_state['opt_type'], required=True),
            "Region": st.column_config.SelectboxColumn("Region", options=st.session_state['opt_region'], required=True),
            "AssetClass": st.column_config.SelectboxColumn("Asset Class", options=st.session_state['opt_asset'], required=True)
        }
        
        edited_df = st.data_editor(df, column_config=column_config, use_container_width=True, hide_index=True, key="reload_editor")
        
        st.markdown("---")
        st.subheader("2. Update Asset")
        if st.button("Update Asset with Reloaded Data", type="primary"):
            if not edited_df.empty:
                row = edited_df.iloc[0]
                handle_reload_save(row, isin)
            else:
                st.error("No data to update.")

    st.write("---")

    # --- MAIN EDIT FORM ---
    # REPLACEMENT 1: Using our central loader instead of the long IF-block
    ensure_reference_data()

    with st.form("edit_form"):
        col1, col2 = st.columns(2)
        col1.text_input("ISIN (Primary Key)", value=isin, disabled=True)
        name = col1.text_input("Name", value=asset["Name"])
        ticker = col2.text_input("Ticker", value=asset["Ticker"])
        currency = col2.text_input("Currency", value=asset["Currency"])
        
        # Hinweis: Die Keys hier (z.B. asset["Asset Class"]) müssen 
        # exakt so heißen wie im flattened_data dict der database.py!
        asset_class = col1.selectbox("Asset Class", st.session_state['opt_asset'], 
                                     index=get_option_index(st.session_state['opt_asset'], asset["Asset Class"]))
        
        region = col2.selectbox("Region", st.session_state['opt_region'], 
                                index=get_option_index(st.session_state['opt_region'], asset["Region"]))
        
        sector = col1.selectbox("Sector", st.session_state['opt_gics'], 
                                index=get_option_index(st.session_state['opt_gics'], asset["Sector"]))
        
        instr_type = col2.selectbox("Instrument Type", st.session_state['opt_type'], 
                                    index=get_option_index(st.session_state['opt_type'], asset["Type"]))
        
        source = col1.selectbox("Price Source", st.session_state['opt_source'], 
                                index=get_option_index(st.session_state['opt_source'], asset["Price Source"]))
        
        industry = col2.text_input("Industry", value=asset["Industry"])
        country = col1.text_input("Country", value=asset["Country"])

        if st.form_submit_button("Save Changes", type="primary"):
            updated_payload = {
                "name": name,
                "ticker": ticker,
                "currency": currency,
                "asset_class_code": extract_code(asset_class),
                "region_code": extract_code(region),
                "sector_code": extract_code(sector),
                "instrument_type_code": extract_code(instr_type), # Korrigiert: _code
                "price_source_code": extract_code(source),       # Korrigiert: _code
                "industry": industry,
                "country": country,
                "updated_at": datetime.now().isoformat(),
                "updated_by": st.session_state.get("user_name", "System")
            }
            update_asset_static_data(isin, updated_payload)
            st.success("Asset updated successfully!")
            # WICHTIG: Cache leeren, damit die Liste die neuen Daten zeigt
            st.cache_data.clear() 
            st.session_state["view"] = "list"
            st.rerun()




