import streamlit as st
from src.database import get_all_assets_with_labels, supabase

def asset_table_view():
    st.title("Asset Static Data")
    
    if st.button("➕ New ISIN"):
        # Prepare temporary storage for the bulk form (lowercase keys)
        st.session_state["rows"] = [{
            "isin": "", "name": "", "ticker": "", "currency": "USD", 
            "price_source": "", "asset_class": "", "region": "", "sector": ""
        }]
        st.session_state["view"] = "form"
        st.rerun()

    # Display the data table
    data = get_all_assets_with_labels()
    if data:
        st.dataframe(data, use_container_width=True)
    else:
        st.info("No records found in asset_static_data.")

