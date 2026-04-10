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
        ["Home", "AssetStaticData", "Transactions", "SearchTicker"], # 'SearchTicker' hinzugefügt
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
        st.write(f"Hello **{st.session_state['user_name']}**, please select a menu item to get started.")

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

# --- PAGE: SEARCH TICKER ---
if menu == "SearchTicker":
    st.title("🔍 Ticker Suche via ISIN")
    st.write("Suche nach Handelsplätzen und Stammdaten mithilfe der ISIN.")

    # Eingabebereich
    col1, col2 = st.columns([3, 1])
    with col1:
        isin_input = st.text_input("ISIN eingeben", placeholder="z.B. US0378331005")
    with col2:
        st.write("##") # Abstandshalter
        search_button = st.button("SearchTicker")

    if search_button and isin_input:
        with st.spinner(f"Suche Ticker für {isin_input}..."):
            try:
                # 1. Suche über yfinance (liefert oft Ticker-Vorschläge)
                search_results = yf.Search(isin_input).quotes
                
                if not search_results:
                    st.warning("Keine Ticker zu dieser ISIN gefunden.")
                else:
                    data_list = []
                    
                    for res in search_results:
                        symbol = res.get("symbol")
                        ticker_obj = yf.Ticker(symbol)
                        info = ticker_obj.info
                        
                        # 2. Handelsvolumen der letzten 7 Tage berechnen
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=7)
                        hist = ticker_obj.history(start=start_date, end=end_date)
                        
                        avg_volume = hist['Volume'].mean() if not hist.empty else 0
                        
                        # Daten sammeln
                        data_list.append({
                            "Ticker": symbol,
                            "Name": info.get("longName") or res.get("longname"),
                            "Currency": info.get("currency"),
                            "Industry": info.get("industry"),
                            "Sector": info.get("sector"),
                            "Trading Volume (7d Avg)": f"{avg_volume:,.0f}"
                        })
                    
                    # 3. Tabelle anzeigen
                    df = pd.DataFrame(data_list)
                    st.subheader("Gefundene Ticker / Handelsplätze")
                    st.dataframe(df, use_container_width=True, hide_index=True)

            except Exception as e:
                st.error(f"Fehler bei der Abfrage: {e}")


