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
    """Main entry point for transaction management. Handles routing between views."""
    current_view = st.session_state.get("view", "list")

    if current_view == "form":
        render_transaction_form()
    elif current_view == "import_preview":
        render_import_preview_screen()
    else:
        render_list_view()

@st.dialog("Import Transactions via CSV")
def show_import_dialog():
    """Dialog window for CSV upload and format configuration."""
    st.write("Please select your CSV file and configure the format.")
    
    uploaded_file = st.file_uploader("Choose CSV file", type="csv")
    
    col1, col2 = st.columns(2)
    separator = col1.selectbox("Separator", options=[",", ";", "\t"], 
                               format_func=lambda x: "Comma" if x == "," else "Semicolon" if x == ";" else "Tab")
    decimal_sep = col2.selectbox("Decimal Separator", options=[",", "."], 
                                 format_func=lambda x: "Comma (,)" if x == "," else "Dot (.)")

    if uploaded_file is not None:
        try:
            # Automatic detection of thousand separator based on decimal separator
            # If decimal is ',', thousands is usually '.' and vice-versa
            thousand_sep = "." if decimal_sep == "," else ","
            
            # Load CSV with pandas
            df = pd.read_csv(
                uploaded_file,
                sep=separator,
                decimal=decimal_sep,
                thousands=thousand_sep,
                quotechar='"',
                skipinitialspace=True
            )
            
            st.write("### Preview of uploaded data:")
            st.dataframe(df, use_container_width=True)
            
            st.info(f"Detected {len(df)} rows. Numbers converted to dot-decimal format.")
            
            if st.form_submit_button("Proceed with Import") or st.button("Proceed with Import", type="primary"):
                # Initialize the 'import_row' column (all checked by default)
                df.insert(0, "import_row", True)
                
                # Store in session state and switch view
                st.session_state["imported_df"] = df
                st.session_state["view"] = "import_preview"
                st.rerun()
                
        except Exception as e:
            st.error(f"Error parsing CSV: {e}")

def render_import_preview_screen():
    """Screen for selecting which rows to import from the CSV."""
    st.title("Review Import Data")
    st.write("Deselect rows that you do not want to import.")

    if "imported_df" not in st.session_state:
        st.error("No data found to import.")
        if st.button("Back to List"):
            st.session_state["view"] = "list"
            st.rerun()
        return

    # Use data_editor to allow checkbox interaction
    # All columns except 'import_row' are disabled for editing
    edited_df = st.data_editor(
        st.session_state["imported_df"],
        column_config={
            "import_row": st.column_config.CheckboxColumn(
                "Import?",
                help="Select to include in database",
                default=True,
            )
        },
        disabled=[col for col in st.session_state["imported_df"].columns if col != "import_row"],
        hide_index=True,
        use_container_width=True,
        key="import_editor"
    )

    col_nav1, col_nav2, _ = st.columns([1, 1, 4])
    
    with col_nav1:
        if st.button("⬅ Back / Cancel"):
            st.session_state["view"] = "list"
            if "imported_df" in st.session_state:
                del st.session_state["imported_df"]
            st.rerun()

    with col_nav2:
        if st.button("🚀 Confirm Selection", type="primary"):
            # Filter only selected rows
            final_selection = edited_df[edited_df["import_row"] == True]
            st.session_state["final_import_data"] = final_selection
            
            st.success(f"Ready to import {len(final_selection)} rows!")
            # Further mapping logic will be implemented here later

def render_list_view():
    """Displays the transaction table and navigation buttons."""
    st.title("Transactions")
    
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
    
    if st.button("⬅ Cancel"):
        st.session_state["view"] = "list"
        st.rerun()

    # Load reference data if not already in session state
    if 'ref_trans_loaded' not in st.session_state:
        user = st.session_state.get("user_name", "System")
        st.session_state['opt_accounts'] = get_account_ref_options(user)
        st.session_state['opt_assets'] = get_asset_ref_options()
        st.session_state['opt_trans_types'] = get_ref_options("ref_transaction_type")
        st.session_state['ref_trans_loaded'] = True

    with st.form("transaction_entry_form"):
        col1, col2 = st.columns(2)
        
        # Selectboxes with "Code (Label)" format
        account_selection = col1.selectbox("Account", st.session_state.get('opt_accounts', []))
        asset_selection = col2.selectbox("Asset (ISIN)", st.session_state.get('opt_assets', []))
        
        type_selection = col1.selectbox("Transaction Type", st.session_state.get('opt_trans_types', []))
        trans_date = col2.date_input("Transaction Date", value=datetime.now())
        
        quantity = col1.number_input("Quantity", step=0.0001, format="%.4f", min_value=0.0)
        amount_eur = col2.number_input("Total Amount (EUR)", step=0.01, format="%.2f", min_value=0.0)

        if st.form_submit_button("Save Transaction", type="primary"):
            # 1. Extract clean codes
            clean_isin = asset_selection.split(" (")[0] if asset_selection else ""
            clean_account = account_selection.split(" (")[0] if account_selection else ""
            clean_type = type_selection.split(" (")[0] if type



