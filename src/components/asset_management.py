import streamlit as st
from src.database import get_all_assets_with_labels
from .ticker_search import ticker_search_view

def asset_table_view():
    # Wechsle die Ansicht basierend auf dem Status
    if st.session_state.get("view") == "search":
        if st.button("⬅ Back to List"):
            st.session_state["view"] = "list"
            st.rerun()
        
        # Hier rufen wir das Suchformular auf
        ticker_search_view()
        
    else:
        st.title("Asset Static Data")
        
        if st.button("➕ New ISIN"):
            st.session_state["view"] = "search"
            st.rerun()

        # Display the data table
        data = get_all_assets_with_labels()
        if data:
            st.dataframe(data, use_container_width=True)
        else:
            st.info("No records found in asset_static_data.")


