import streamlit as st 
from src.authentication import check_password 
from src.database import get_all_assets_with_labels
from src.components import asset_table_view, transaction_table_view, ticker_search_view 

st.set_page_config(page_title="Asset Manager", layout="wide") 

if check_password(): 
    st.sidebar.title(f"User: {st.session_state['user_name']}") 
    menu = st.sidebar.radio("Navigation", ["Home", "AssetStaticData", "Transactions"]) 
    
    if st.sidebar.button("Logout"): 
        st.session_state["logged_in"] = False 
        st.rerun() 

    # State Management
    if "view" not in st.session_state: st.session_state["view"] = "list"
    if st.session_state.get("last_menu") != menu:
        st.session_state["view"] = "list"
        st.session_state["last_menu"] = menu 

    if menu == "Home":
        st.title("Welcome")
        st.write(f"Hello **{st.session_state['user_name']}**.")

    elif menu == "AssetStaticData":
        asset_table_view() 

    elif menu == "Transactions":
        if st.session_state["view"] == "list":
            transaction_table_view()
        else:
            st.warning("Bulk Form noch nicht implementiert.") # Platzhalter statt Absturz

    elif menu == "SearchTicker":
        ticker_search_view()

