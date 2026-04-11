import streamlit as st
import uuid
from datetime import datetime
from src.database import (
    get_all_transactions, 
    get_ref_options, 
    get_asset_ref_options, 
    get_account_ref_options,
    save_transaction
)

def transaction_table_view():
    """Main entry point for transaction management."""
    # View routing logic similar to asset management [cite: 15]
    current_view = st.session_state.get("view", "list")

    if current_view == "form":
        render_transaction_form()
    else:
        render_list_view()

def render_list_view():
    """Displays the table of existing transactions."""
    st.title("Transactions")
    
    if st.button("➕ New Transaction"):
        # Switch to form view 
        st.session_state["view"] = "form"
        st.rerun()

    data = get_all_transactions()
    if data:
        # Display data fetched from Supabase [cite: 66]
        st.dataframe(data, use_container_width=True, hide_index=True)
    else:
        st.info("No records found in transactions.")

def render_transaction_form():
    """Renders the form to create a new transaction."""
    st.subheader("Create New Transaction")
    
    if st.button("⬅ Cancel"):
        st.session_state["view"] = "list"
        st.rerun()

    # Load reference data into session state to avoid multiple DB hits [cite: 30, 42]
    if 'ref_trans_loaded' not in st.session_state:
        user = st.session_state.get("user_name", "System")
        st.session_state['opt_accounts'] = get_account_ref_options(user)
        st.session_state['opt_assets'] = get_asset_ref_options()
        st.session_state['opt_trans_types'] = get_ref_options("ref_transaction_type")
        st.session_state['ref_trans_loaded'] = True

    with st.form("transaction_entry_form"):
        col1, col2 = st.columns(2)
        
        # Dropdowns using "Code (Label)" format as requested
        account = col1.selectbox("Account", st.session_state['opt_accounts'])
        asset = col2.selectbox("Asset (ISIN)", st.session_state['opt_assets'])
        
        trans_type = col1.selectbox("Transaction Type", st.session_state['opt_trans_types'])
        date = col2.date_input("Transaction Date", value=datetime.now())
        
        quantity = col1.number_input("Quantity", step=0.0001, format="%.4f")
        amount = col2.number_input("Total Amount (EUR)", step=0.01, format="%.2f")

        if st.form_submit_button("Save Transaction", type="primary"):
            # Extract code from "Code (Label)" format using split 
            new_payload = {
                "username": st.session_state["user_name"],
                "id": str(uuid.uuid4())[:8], # Generate unique short ID [cite: 80]
                "account_code": account.split(" (")[0],
                "isin": asset.split(" (")[0],
                "type_code": trans_type.split(" (")[0],
                "date": date.isoformat(),
                "quantity": quantity,
                "total_amount_eur": amount
            }
            
            try:
                save_transaction(new_payload)
                st.success("Transaction successfully recorded!")
                # Clear cache to refresh the list view [cite: 28, 35]
                st.cache_data.clear()
                st.session_state["view"] = "list"
                # Reset ref trigger for next use
                if 'ref_trans_loaded' in st.session_state: 
                    del st.session_state['ref_trans_loaded']
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save transaction: {e}")

