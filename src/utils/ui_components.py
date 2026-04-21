import streamlit as st
import pandas as pd
import yfinance as yf

def apply_advanced_filters(df: pd.DataFrame, session_prefix: str, custom_filter_logic: dict = None) -> pd.DataFrame:
    """
    Renders a unified Advanced Query Builder UI and returns the filtered DataFrame.
    
    :param df: The original DataFrame to filter.
    :param session_prefix: Unique prefix for session state keys (e.g., 'asset' or 'import').
    :param custom_filter_logic: Optional dict mapping column names to custom UI/logic functions.
    """
    rules_key = f"{session_prefix}_filter_rules"
    
    if rules_key not in st.session_state:
        st.session_state[rules_key] = []

    with st.expander("🛠 Advanced Query Builder", expanded=False):
        logic_mode = st.radio(
            "Combination Logic", 
            ["Match ALL (AND)", "Match ANY (OR)"], 
            horizontal=True, 
            key=f"{session_prefix}_logic"
        )
        
        c1, c2 = st.columns([1, 4])
        if c1.button("➕ Add Rule", key=f"{session_prefix}_add"):
            st.session_state[rules_key].append({"column": df.columns[0]})
        
        if c2.button("🗑 Clear All", key=f"{session_prefix}_clear"):
            st.session_state[rules_key] = []
            st.rerun()

        active_filters = []
        for i, rule in enumerate(st.session_state[rules_key]):
            r_col1, r_col2, r_col3 = st.columns([2, 3, 0.5])
            
            col_name = r_col1.selectbox(
                f"Column {i}", df.columns, 
                key=f"{session_prefix}_col_{i}"
            )
            
            # Use custom logic if provided (e.g., for Date/Status fields)
            if custom_filter_logic and col_name in custom_filter_logic:
                mask = custom_filter_logic[col_name](df, r_col2, i, session_prefix)
                if mask is not None:
                    active_filters.append(mask)
            else:
                # Standard Logic: Multiselect for unique values
                options = sorted(df[col_name].dropna().unique().astype(str).tolist())
                selected_vals = r_col2.multiselect(
                    f"Values {i}", options, 
                    key=f"{session_prefix}_val_{i}"
                )
                if selected_vals:
                    active_filters.append(df[col_name].astype(str).isin(selected_vals))

            if r_col3.button("❌", key=f"{session_prefix}_rem_{i}"):
                st.session_state[rules_key].pop(i)
                st.rerun()

    # Apply the masks
    if not active_filters:
        return df

    mask = active_filters[0]
    for m in active_filters[1:]:
        mask = (mask & m) if logic_mode == "Match ALL (AND)" else (mask | m)
    
    return df[mask]


# --- YFINANCE SEARCH HELPER FUNCTIONS ---

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


def yfinance_search_component(search_input, session_key_prefix="search", allow_isin_edit=True):
    """
    Reusable component for yfinance search with results grid and selection.
    
    Args:
        search_input: The search term (ISIN, ticker, or name)
        session_key_prefix: Prefix for session state keys to avoid conflicts
        allow_isin_edit: Whether to allow editing ISIN in the data editor
    
    Returns:
        tuple: (selected_row, edited_df) or (None, None) if no selection
    """
    results_key = f"{session_key_prefix}_results_df"
    editor_key = f"{session_key_prefix}_editor"
    
    if st.button("yfinance search") and search_input:
        with st.spinner("Fetching data from Yahoo Finance..."):
            try:
                search_results = yf.Search(search_input).quotes
                if not search_results:
                    st.warning("No results found.")
                    return None, None
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
                    st.session_state[results_key] = df
                    st.rerun()
            except Exception as e:
                st.error(f"Search failed: {e}")
                return None, None

    if results_key in st.session_state:
        df = st.session_state[results_key]
        st.subheader("1. Review & Edit Data")
        if allow_isin_edit:
            st.info("The ISIN is mandatory for saving. If the field is empty, please enter it manually in the table below.")
        
        column_config = {
            "ISIN": st.column_config.TextColumn("ISIN" + (" (Edit if empty)" if allow_isin_edit else ""), disabled=not allow_isin_edit),
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
        
        edited_df = st.data_editor(df, column_config=column_config, use_container_width=True, hide_index=True, key=editor_key)
        
        st.markdown("---")
        st.subheader("2. Select Ticker")
        selected_ticker = st.selectbox("Select ticker:", options=edited_df["Ticker"].tolist(), key=f"{session_key_prefix}_ticker_select")
        
        if selected_ticker:
            selected_row = edited_df[edited_df["Ticker"] == selected_ticker].iloc[0]
            return selected_row, edited_df
        
    return None, None

