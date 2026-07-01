import os

import requests
import streamlit as st

from src.authentication import check_password, logout, user_settings_ui
from src.database import initialize_runtime_from_streamlit

st.set_page_config(page_title="Asset Manager", layout="wide")
initialize_runtime_from_streamlit(st)


def _ensure_backend_ready() -> None:
    backend_url = os.environ.get("BACKEND_API_URL", "").strip().rstrip("/")
    if not backend_url:
        st.error(
            "Missing BACKEND_API_URL. Start FastAPI and set BACKEND_API_URL for this Streamlit process."
        )
        st.stop()

    try:
        response = requests.get(f"{backend_url}/health", timeout=5)
        response.raise_for_status()
        payload = response.json() if response.content else {}
    except Exception as exc:
        st.error(f"Cannot reach backend at {backend_url}. Details: {exc}")
        st.stop()

    if isinstance(payload, dict) and payload.get("runtime_initialized") is False:
        st.error(
            "Backend is reachable but runtime is not initialized. "
            "Check Supabase environment variables in the FastAPI process."
        )
        st.stop()


_ensure_backend_ready()


if check_password():
    # ERST HIER: Komponenten importieren, nachdem der Login erfolgreich war
    from src.components import asset_table_view, transaction_table_view, admin_approval_page, accounts_settings_view, price_management_view, render_holdings_view

    st.sidebar.title(f"User: {st.session_state['user_name']}")

    # 1. Basis-Menüoptionen für ALLE User definieren
    menu_options = ["Home", "User Settings", "Accounts Settings", "Transactions", "Holdings"]
    
    # 2. Admin-Menüpunkte nur für Admins hinzufügen
    if st.session_state.get("is_admin"):
        # Fügt die Admin-Punkte hinzu (Reihenfolge kannst du hier beliebig anpassen)
        menu_options.extend([
            "🔒 Admin: Asset Data", 
            "🔒 Admin: Price Data", 
            "🔒 Admin: Console"
        ])
    
    # 3. Sidebar-Radio rendern
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

    elif menu == "User Settings":
        user_settings_ui()

    elif menu == "Accounts Settings":
        accounts_settings_view()

    elif menu == "Transactions":
        transaction_table_view()

    elif menu == "Holdings":
        render_holdings_view()

    # Admin-geschützte Routen (zusätzliche Sicherheitsprüfung via 'and')
    elif menu == "🔒 Admin: Asset Data" and st.session_state.get("is_admin"):
        asset_table_view()

    elif menu == "🔒 Admin: Price Data" and st.session_state.get("is_admin"):
        price_management_view()

    elif menu == "🔒 Admin: Console" and st.session_state.get("is_admin"):
        admin_approval_page()


