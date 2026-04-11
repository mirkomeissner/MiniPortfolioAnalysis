import streamlit as st  
from src.authentication import check_password  
from src.components import asset_table_view, transaction_table_view  
 
st.set_page_config(page_title="Asset Manager", layout="wide")  
 
if check_password():  
    st.sidebar.title(f"User: {st.session_state['user_name']}")  
    # English Navigation
    menu = st.sidebar.radio("Navigation", ["Home", "Asset Data", "Transactions"])  
     
    if st.sidebar.button("Logout"):  
        st.session_state["logged_in"] = False  
        st.rerun()  
 
    # State Management 
    if "view" not in st.session_state: 
        st.session_state["view"] = "list" 
    
    if st.session_state.get("last_menu") != menu: 
        st.session_state["view"] = "list" 
        st.session_state["last_menu"] = menu  
 
    if menu == "Home": 
        st.title("Welcome") 
        st.write(f"Hello **{st.session_state['user_name']}**, please use the sidebar to navigate.") 
 
    elif menu == "Asset Data": 
        asset_table_view()  
 
    elif menu == "Transactions": 
        if st.session_state["view"] == "list": 
            transaction_table_view() 
        else: 
            st.warning("Bulk Form not yet implemented.")

