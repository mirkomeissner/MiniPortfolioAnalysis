import streamlit as st
from src.database import get_all_transactions

def transaction_table_view():
    st.title("Transactions")
    
    # Button to switch to form view
    if st.button("➕ New Transaction"):
        # Initialize rows for bulk input (similar to assets)
        st.session_state["rows"] = [{
            "ID": "", "AccountCode": "", "ISIN": "", 
            "Date": None, "TypeCode": "", "Quantity": 0.0, "TotalAmountEUR": 0.0
        }]
        st.session_state["view"] = "form"
        st.rerun()

    # Display the data table
    data = get_all_transactions()
    if data:
        st.dataframe(data, use_container_width=True)
    else:
        st.info("No records found in Transactions.")

def transaction_bulk_form():
    st.title("Add New Transactions")
    st.write("Form logic for bulk insert goes here...")
    if st.button("Back to List"):
        st.session_state["view"] = "list"
        st.rerun()


