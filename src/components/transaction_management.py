import streamlit as st
import pandas as pd
import io
import uuid
from datetime import datetime
from src.database import (
    get_all_transactions, 
    get_ref_options, 
    get_asset_ref_options, 
    get_account_ref_options,
    save_transaction,
    get_next_transaction_count
)

def transaction_table_view():
    """Main component for transactions."""
    # Check the current view state
    current_view = st.session_state.get("view", "list")

    if current_view == "form":
        render_transaction_form()
    else:
        render_list_view()

def render_list_view():
    """Displays the transaction table and navigation buttons."""
    st.title("Transactions")
    
    # Create two columns for the buttons
    col_btn1, col_btn2, _ = st.columns([1, 1, 4])
    
    with col_btn1:
        if st.button("➕ New Transaction", use_container_width=True):
            st.session_state["view"] = "form"
            st.rerun()
            
    with col_btn2:
        if st.button("📥 Import CSV", use_container_width=True):
            show_import_dialog()

    data = get_all_transactions()
    if data:
        st.dataframe(data, use_container_width=True, hide_index=True)
    else:
        st.info("No records found in transactions.")



def render_transaction_form():
    """Renders the input form to create a new transaction with a custom ID logic."""
    st.subheader("Create New Transaction")
    
    # Back button to return to the list view
    if st.button("⬅ Cancel"):
        st.session_state["view"] = "list"
        st.rerun()

    # Load reference data for dropdowns using the "Code (Label)" pattern [cite: 32]
    if 'ref_trans_loaded' not in st.session_state:
        user = st.session_state.get("user_name", "System")
        st.session_state['opt_accounts'] = get_account_ref_options(user)
        st.session_state['opt_assets'] = get_asset_ref_options()
        st.session_state['opt_trans_types'] = get_ref_options("ref_transaction_type")
        st.session_state['ref_trans_loaded'] = True

    with st.form("transaction_entry_form"):
        col1, col2 = st.columns(2)
        
        # User selects from "Code (Label)" formatted strings [cite: 32]
        account_selection = col1.selectbox("Account", st.session_state.get('opt_accounts', []))
        asset_selection = col2.selectbox("Asset (ISIN)", st.session_state.get('opt_assets', []))
        
        type_selection = col1.selectbox("Transaction Type", st.session_state.get('opt_trans_types', []))
        trans_date = col2.date_input("Transaction Date", value=datetime.now())
        
        # Numeric inputs for quantity and amount 
        quantity = col1.number_input("Quantity", step=0.0001, format="%.4f", min_value=0.0)
        amount_eur = col2.number_input("Total Amount (EUR)", step=0.01, format="%.2f", min_value=0.0)

        if st.form_submit_button("Save Transaction", type="primary"):
            # 1. Extract clean codes from the "Code (Label)" selection [cite: 33, 34, 39]
            clean_isin = asset_selection.split(" (")[0] if asset_selection else ""
            clean_account = account_selection.split(" (")[0] if account_selection else ""
            clean_type = type_selection.split(" (")[0] if type_selection else ""
            
            # 2. Date formatting for the ID (YYYYMMDD) and DB (ISO)
            id_date_str = trans_date.strftime("%Y%m%d")
            db_date_str = trans_date.isoformat()

            # 3. Calculate the counter for the ID (ISIN_Date_Count)
            # This function must be implemented in src/database.py
            current_count = get_next_transaction_count(
                st.session_state["user_name"], 
                clean_isin, 
                db_date_str
            )
            count_suffix = f"{current_count:03d}"

            # 4. Construct the custom ID
            generated_id = f"{clean_isin}_{id_date_str}_{count_suffix}"

            # 5. Prepare the data payload for Supabase [cite: 80, 81]
            new_payload = {
                "username": st.session_state["user_name"],
                "id": generated_id,
                "account_code": clean_account,
                "isin": clean_isin,
                "date": db_date_str,
                "type_code": clean_type,
                "quantity": quantity,
                "total_amount_eur": amount_eur
            }
            
            try:
                save_transaction(new_payload)
                st.success(f"Transaction saved! ID: {generated_id}")
                
                # Refresh data and return to list view
                st.cache_data.clear()
                st.session_state["view"] = "list"
                
                # Reset local ref data flag for the next form entry
                if 'ref_trans_loaded' in st.session_state: 
                    del st.session_state['ref_trans_loaded']
                    
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save transaction: {e}")




@st.dialog("Import Transactions via CSV")
def show_import_dialog():
    """Dialog window for CSV upload and configuration."""
    st.write("Please select your CSV file and configure the format.")
    
    uploaded_file = st.file_uploader("Choose CSV file", type="csv")
    
    col1, col2 = st.columns(2)
    separator = col1.selectbox("Separator", options=[",", ";", "\t"], format_func=lambda x: "Comma" if x == "," else "Semicolon" if x == ";" else "Tab")
    decimal_sep = col2.selectbox("Decimal Separator", options=[",", "."], format_func=lambda x: "Comma (,)" if x == "," else "Dot (.)")

    if uploaded_file is not None:
        try:
            # We read the file as text first to handle manual cleaning if needed
            # or use pandas' powerful parsing engine
            
            # Logic for Thousand Separator: 
            # If decimal is ',', thousands is usually '.' (and vice-versa)
            thousand_sep = "." if decimal_sep == "," else ","
            
            df = pd.read_csv(
                uploaded_file,
                sep=separator,
                decimal=decimal_sep,
                thousands=thousand_sep,
                quotechar='"', # Handles quotes around values automatically
                skipinitialspace=True
            )
            
            st.write("### Preview of uploaded data:")
            st.dataframe(df, use_container_width=True)
            
            st.info(f"Detected {len(df)} rows. All numbers have been converted to dot-decimal format.")

            if st.button("Proceed with Import", type="primary"):
                # Initialize the 'import_row' column (all checked by default)
                df.insert(0, "import_row", True)
                
                # Store in session state
                st.session_state["imported_df"] = df
                st.session_state["view"] = "import_preview"
                st.rerun()
                
        except Exception as e:
            st.error(f"Error parsing CSV: {e}")

            



