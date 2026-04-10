import streamlit as st
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
        ["Home", "AssetStaticData", "Transactions"],
        index=0  # 'Home' is default selection
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
