import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Importing our custom modules from the src folder
from src.authentication import check_password
from src.database import (
    get_ref_data, 
    get_all_assets_with_labels, 
    supabase
)
from src.components import (
    asset_table_view, 
    asset_bulk_form, 
    transaction_table_view, 
    transaction_bulk_form
)

# Page Configuration (Must be first)
st.set_page_config(page_title="Asset Manager", layout="wide")

# Authentication Check
if check_password():
    # --- SIDEBAR ---
    st.sidebar.title(f"User: {st.session_state['user_name']}")
    
    # Navigation Menu
    menu = st.sidebar.radio(
        "Navigation", 
        ["Home", "AssetStaticData", "Transactions", "SearchTicker"], 
        index=0 
    )
    
    # Logout Logic
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

    # --- GLOBAL VIEW STATE MANAGEMENT ---
    # Ensure "view" is always initialized
    if "view" not in st.session_state:
        st.session_state["view"] = "list"

    # Reset view state when switching menu items
    if "last_menu" not in st.session_state:
        st.session_state["last_menu"] = menu
    
    if st.session_state["last_menu"] != menu:
        st.session_state["view"] = "list"
        st.session_state["last_menu"] = menu
    
    # --- MAIN CONTENT AREA ---
    
    # PAGE: HOME
    if menu == "Home":
        st.title("Welcome")
        st.write(f"Hello **{st.session_state['user_name']}**, please select a menu item to get started. Made in Merzhausen with Love.")

    # PAGE: ASSET STATIC DATA
    elif menu == "AssetStaticData":
        if st.session_state["view"] == "list":
            asset_table_view()
        elif st.session_state["view"] == "form":
            asset_bulk_form()
            
    # PAGE: Transactions
    elif menu == "Transactions":
        if st.session_state["view"] == "list":
            transaction_table_view()
        elif st.session_state["view"] == "form":
            transaction_bulk_form()
    # PAGE: SEARCH TICKER
    elif menu == "SearchTicker":
        st.title("🔍 Ticker Suche via ISIN")
        
        # Extended Mapping based on your categories
        region_map = {
            # USA
            'United States': 'USA',
            
            # NAM (North America Ex-USA)
            'Canada': 'NAM', 'Bermuda': 'NAM',
            
            # UK
            'United Kingdom': 'UK', 'Jersey': 'UK', 'Guernsey': 'UK', 'Isle of Man': 'UK',
            
            # EUR (Europe Ex-UK)
            'Germany': 'EUR', 'France': 'EUR', 'Italy': 'EUR', 'Spain': 'EUR', 
            'Netherlands': 'EUR', 'Switzerland': 'EUR', 'Belgium': 'EUR', 
            'Austria': 'EUR', 'Ireland': 'EUR', 'Sweden': 'EUR', 'Norway': 'EUR', 
            'Denmark': 'EUR', 'Finland': 'EUR', 'Portugal': 'EUR', 'Luxembourg': 'EUR',
            
            # APAC (Asia Pacific Developed)
            'Japan': 'APAC', 'Australia': 'APAC', 'Singapore': 'APAC', 
            'New Zealand': 'APAC', 'Hong Kong': 'APAC',
            
            # EM (Emerging Markets - Asia/East Europe)
            'China': 'EM', 'India': 'EM', 'Taiwan': 'EM', 'South Korea': 'EM', 
            'Indonesia': 'EM', 'Thailand': 'EM', 'Malaysia': 'EM', 'Philippines': 'EM', 
            'Vietnam': 'EM', 'Russia': 'EM', 'Poland': 'EM', 'Turkey': 'EM', 
            'Czech Republic': 'EM', 'Hungary': 'EM', 'Greece': 'EM',
            
            # LATM (Latin America)
            'Brazil': 'LATM', 'Mexico': 'LATM', 'Chile': 'LATM', 'Colombia': 'LATM', 
            'Peru': 'LATM', 'Argentina': 'LATM',
            
            # MEAF (Middle East & Africa)
            'South Africa': 'MEAF', 'Israel': 'MEAF', 'Saudi Arabia': 'MEAF', 
            'United Arab Emirates': 'MEAF', 'Qatar': 'MEAF', 'Kuwait': 'MEAF', 
            'Egypt': 'MEAF', 'Nigeria': 'MEAF'
        }

        isin_input = st.text_input("ISIN eingeben", placeholder="z.B. US0378331005")
        search_button = st.button("SearchTicker")

        if search_button and isin_input:
            with st.spinner(f"Suche nach {isin_input}..."):
                try:
                    search_results = yf.Search(isin_input).quotes
                    if not search_results:
                        st.warning("Keine Ergebnisse gefunden.")
                    else:
                        data_list = []
                        for res in search_results:
                            symbol = res.get("symbol")
                            ticker_obj = yf.Ticker(symbol)
                            info = ticker_obj.info
                            
                            # Logic for Region Mapping
                            country = info.get("country", "Unknown")
                            name = info.get("longName") or res.get("longname") or ""
                            
                            # Heuristic for Global/Developed (especially for ETFs)
                            if any(word in name.upper() for word in ["WORLD", "GLOBAL", "ALL COUNTRY"]):
                                mapped_region = "GLO"
                            elif "DEVELOPED" in name.upper():
                                mapped_region = "DEV"
                            else:
                                # Standard country mapping, fallback to GLO if unknown
                                mapped_region = region_map.get(country, "GLO")

                            # Volume 7d
                            hist = ticker_obj.history(period="7d")
                            avg_vol = hist['Volume'].mean() if not hist.empty else 0
                            
                            data_list.append({
                                "Ticker": symbol,
                                "Name": name,
                                "Region": mapped_region,
                                "Country": country,
                                "Exchange": info.get("exchange"),
                                "Currency": info.get("currency"),
                                "Industry": info.get("industry"),
                                "Vol (7d Avg)": f"{avg_vol:,.0f}"
                            })
                        
                        st.dataframe(pd.DataFrame(data_list), use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"Fehler: {e}")

