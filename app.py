import streamlit as st  
from src.authentication import check_password, logout, user_settings_ui  

st.set_page_config(page_title="Asset Manager", layout="wide")  

if check_password():  
    # ERST HIER: Komponenten importieren, nachdem der Login erfolgreich war
    from src.components import asset_table_view, transaction_table_view, admin_approval_page

    st.sidebar.title(f"User: {st.session_state['user_name']}")  

    # 1. Menüoptionen definieren
    menu_options = ["Home", "User Settings", "Asset Data", "Transactions"]
    
    # 2. Admin Console hinzufügen
    if st.session_state.get("is_admin"):
        menu_options.append("Admin Console")
    
    menu = st.sidebar.radio("Navigation", menu_options)

    if st.sidebar.button("Logout"):  
        logout()

    # State Management 
    if "view" not in st.session_state: 
        st.session_state["view"] = "list" 
    
    if st.session_state.get("last_menu") != menu: 
        st.session_state["view"] = "list" 
        st.session_state["last_menu"] = menu  

    # Routing
    if menu == "Home": 
        st.title("Welcome") 
        st.write(f"Hello **{st.session_state['user_name']}**, please use the sidebar to navigate.") 

    elif menu == "Admin Console" and st.session_state.get("is_admin"):
        admin_approval_page()
 
    elif menu == "Asset Data": 
        asset_table_view()  
 
    elif menu == "Transactions": 
        transaction_table_view()
    
    elif menu == "User Settings":
        user_settings_ui()
