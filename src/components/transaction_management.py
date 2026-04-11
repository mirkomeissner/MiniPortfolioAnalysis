import streamlit as st
from src.database import get_all_transactions

def transaction_table_view():
    # UI Title (can stay capitalized)
    st.title("Transactions")
    
    # Button to switch to form view
    if st.button("➕ New Transaction"):
        # Initialize rows for bulk input (keys now lowercase to match DB)
        st.session_state["rows"] = [{
            "id": "", 
            "account_code": "", 
            "isin": "", 
            "date": None, 
            "type_code": "", 
            "quantity": 0.0, 
            "total_amount_eur": 0.0
        }]
        st.session_state["view"] = "form"
        st.rerun()

    # Display the data table
    data = get_all_transactions()
    if data:
        # data contains lowercase keys from Supabase (username, id, isin, etc.)
        st.dataframe(data, use_container_width=True)
    else:
        st.info("No records found in transactions.")


