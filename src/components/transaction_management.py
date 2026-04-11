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
    elif current_view == "import_upload":
        render_import_upload_screen()
    elif current_view == "import_preview":
        render_import_preview_screen()
    else:
        render_list_view()

def render_import_upload_screen():
    """Screen for CSV upload and format configuration."""
    st.subheader("Import Transactions via CSV")
    
    if st.button("⬅ Cancel"):
        st.session_state["view"] = "list"
        st.rerun()

    st.write("Please select your CSV file and configure the format.")
    
    uploaded_file = st.file_uploader("Choose CSV file", type="csv")
    
    col1, col2 = st.columns(2)
    separator = col1.selectbox("Separator", options=[",", ";", "\t"], 
                               format_func=lambda x: "Comma" if x == "," else "Semicolon" if x == ";" else "Tab")
    decimal_sep = col2.selectbox("Decimal Separator", options=[",", "."], 
                                 format_func=lambda x: "Comma (,)" if x == "," else "Dot (.)")

    if uploaded_file is not None:
        try:
            # Thousand separator logic
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
            
            if st.button("Proceed with Import", type="primary"):
                # Initialize the 'import_row' column (all checked by default)
                df.insert(0, "import_row", True)
                
                # Store in session state and switch view
                st.session_state["imported_df"] = df
                st.session_state["view"] = "import_preview"
                st.rerun()
                
        except Exception as e:
            st.error(f"Error parsing CSV: {e}")


def render_import_preview_screen():
    """
    Revised Import Screen:
    1. Global Settings
    2. Data Preview with Advanced Filtering (AND/OR)
    3. Transaction Type Mapping
    4. Field Mapping
    """
    st.title("Finalize Import: Filter & Map")

    if "imported_df" not in st.session_state:
        st.session_state["view"] = "list"
        st.rerun()
        return

    # Base data from CSV
    df_raw = st.session_state["imported_df"].copy()
    csv_columns = df_raw.columns.tolist()
    user = st.session_state.get("user_name", "System")

    # --- SECTION 1: GLOBAL SETTINGS ---
    st.subheader("1. Global Settings")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        accounts = get_account_ref_options(user)
        selected_account = st.selectbox("Target Account", accounts)
    with col_g2:
        st.caption("Select the account where these transactions will be booked.")

    st.divider()

    # --- SECTION 2: DATA PREVIEW & ADVANCED FILTERING ---
    st.subheader("2. Filter & Select Rows")
    
    # ADVANCED QUERY BUILDER (Consistent with Asset View)
    with st.expander("🛠 Advanced Query Builder", expanded=False):
        logic_mode = st.radio("Combination Logic", ["Match ALL (AND)", "Match ANY (OR)"], horizontal=True)
        
        if "import_filter_rules" not in st.session_state:
            st.session_state["import_filter_rules"] = []
        
        c1, c2 = st.columns([1, 4])
        if c1.button("➕ Add Rule"):
            st.session_state["import_filter_rules"].append({"column": csv_columns[0], "value": None})
            st.rerun()
        if c2.button("🗑 Clear All Filters"):
            st.session_state["import_filter_rules"] = []
            st.rerun()

        active_filters = []
        for i, rule in enumerate(st.session_state["import_filter_rules"]):
            r_col1, r_col2, r_col3 = st.columns([2, 3, 0.5])
            col_name = r_col1.selectbox(f"Column {i}", csv_columns, key=f"fcol_{i}")
            
            # Standard Multiselect Logic for CSV columns
            options = sorted(df_raw[col_name].dropna().unique().astype(str).tolist())
            val = r_col2.multiselect(f"Values {i}", options, key=f"fval_{i}")
            
            if val:
                active_filters.append(df_raw[col_name].astype(str).isin(val))

            if r_col3.button("❌", key=f"frem_{i}"):
                st.session_state["import_filter_rules"].pop(i)
                st.rerun()

    # Apply Filters to the dataframe
    filtered_df = df_raw.copy()
    if active_filters:
        mask = active_filters[0]
        for m in active_filters[1:]:
            mask = (mask & m) if logic_mode == "Match ALL (AND)" else (mask | m)
        filtered_df = df_raw[mask]

    st.info(f"Filtering: {len(filtered_df)} of {len(df_raw)} rows match your criteria.")

    # Interactive Table with Checkboxes
    # Note: 'import_row' was added in the previous upload step
    edited_df = st.data_editor(
        filtered_df,
        column_config={
            "import_row": st.column_config.CheckboxColumn("Import?", default=True)
        },
        disabled=[col for col in filtered_df.columns if col != "import_row"],
        hide_index=True,
        use_container_width=True,
        key="import_editor_final"
    )

    st.divider()

    # --- SECTION 3: TRANSACTION TYPE MAPPING ---
    st.subheader("3. Transaction Type Mapping")
    col_t1, col_t2 = st.columns([1, 2])
    with col_t1:
        # User identifies which column holds the type (Buy/Sell/etc)
        type_column = st.selectbox("CSV Column for Type", csv_columns, 
                                   index=next((i for i, c in enumerate(csv_columns) if "type" in c.lower()), 0))
    
    distinct_csv_types = filtered_df[type_column].unique().tolist()
    db_trans_types = get_ref_options("ref_transaction_type")
    
    type_mapping = {}
    m_col1, m_col2 = st.columns(2)
    for i, csv_val in enumerate(distinct_csv_types):
        target_col = m_col1 if i % 2 == 0 else m_col2
        type_mapping[csv_val] = target_col.selectbox(f"CSV: '{csv_val}' → Map to:", 
                                                     options=db_trans_types, key=f"tmap_{csv_val}")

    st.divider()

    # --- SECTION 4: FIELD MAPPING ---
    st.subheader("4. Field Mapping")
    
    def find_idx(keyword):
        for i, col in enumerate(csv_columns):
            if keyword.lower() in col.lower(): return i
        return 0

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        map_isin = st.selectbox("ISIN Column", csv_columns, index=find_idx("isin"))
        map_date = st.selectbox("Date Column", csv_columns, index=find_idx("date"))
        map_qty  = st.selectbox("Quantity Column", csv_columns, index=find_idx("qty"))
    with col_m2:
        map_trade_amt = st.selectbox("Trade Amount Column", csv_columns, index=find_idx("amount"))
        map_trade_curr = st.selectbox("Trade Currency Column", csv_columns, index=find_idx("curr"))
        map_amt_eur = st.selectbox("Amount in EUR (Optional)", ["<Not in CSV>"] + csv_columns, index=0)

    # --- SECTION 5: IMPORT EXECUTION ---
    st.divider()
    col_nav1, col_nav2, _ = st.columns([1, 1, 4])
    
    with col_nav1:
        if st.button("⬅ Back / Cancel"):
            st.session_state["view"] = "import_upload"
            st.rerun()

    with col_nav2:
        if st.button("🚀 Start Import", type="primary"):
            final_selection = edited_df[edited_df["import_row"] == True]
            
            if final_selection.empty:
                st.error("No rows selected for import.")
                return

            success_count = 0
            error_count = 0
            progress_bar = st.progress(0)
            
            for i, (idx, row) in enumerate(final_selection.iterrows()):
                try:
                    # Logic same as before
                    clean_type = type_mapping[row[type_column]].split(" (")[0]
                    raw_date = pd.to_datetime(row[map_date])
                    db_date_str = raw_date.date().isoformat()
                    id_date_str = raw_date.strftime("%Y%m%d")
                    clean_isin = str(row[map_isin]).strip()

                    count = get_next_transaction_count(user, clean_isin, db_date_str)
                    generated_id = f"{clean_isin}_{id_date_str}_{count:03d}"

                    payload = {
                        "username": user,
                        "id": generated_id,
                        "account_code": selected_account.split(" (")[0],
                        "isin": clean_isin,
                        "date": db_date_str,
                        "type_code": clean_type,
                        "quantity": float(row[map_qty]),
                        "trade_amount": float(row[map_trade_amt]),
                        "trade_currency": str(row[map_trade_curr]).upper().strip()[:3],
                        "amount_eur": float(row[map_amt_eur]) if map_amt_eur != "<Not in CSV>" else None
                    }
                    
                    save_transaction(payload)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    st.error(f"Error row {i+1}: {e}")
                
                progress_bar.progress((i + 1) / len(final_selection))

            st.success(f"Done! {success_count} imported, {error_count} failed.")
            st.cache_data.clear()
            if st.button("Finish"):
                if "imported_df" in st.session_state: del st.session_state["imported_df"]
                st.session_state["view"] = "list"
                st.rerun()




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
            st.session_state["view"] = "import_upload"
            st.rerun()

    data = get_all_transactions()
    if data:
        st.dataframe(data, use_container_width=True, hide_index=True)
    else:
        st.info("No records found in transactions.")

def render_transaction_form():
    """Renders the input form with custom ID logic."""
    st.subheader("Create New Transaction")
    
    if st.button("⬅ Cancel"):
        st.session_state["view"] = "list"
        st.rerun()

    if 'ref_trans_loaded' not in st.session_state:
        user = st.session_state.get("user_name", "System")
        st.session_state['opt_accounts'] = get_account_ref_options(user)
        st.session_state['opt_assets'] = get_asset_ref_options()
        st.session_state['opt_trans_types'] = get_ref_options("ref_transaction_type")
        st.session_state['ref_trans_loaded'] = True

    with st.form("transaction_entry_form"):
        col1, col2 = st.columns(2)
        account_selection = col1.selectbox("Account", st.session_state.get('opt_accounts', []))
        asset_selection = col2.selectbox("Asset (ISIN)", st.session_state.get('opt_assets', []))
        type_selection = col1.selectbox("Transaction Type", st.session_state.get('opt_trans_types', []))
        trans_date = col2.date_input("Transaction Date", value=datetime.now())
        quantity = col1.number_input("Quantity", step=0.0001, format="%.4f", min_value=0.0)
        amount_eur = col2.number_input("Total Amount (EUR)", step=0.01, format="%.2f", min_value=0.0)

        if st.form_submit_button("Save Transaction", type="primary"):
            clean_isin = asset_selection.split(" (")[0] if asset_selection else ""
            id_date_str = trans_date.strftime("%Y%m%d")
            db_date_str = trans_date.isoformat()
            
            # Logic for structured ID
            current_count = get_next_transaction_count(
                st.session_state["user_name"], 
                clean_isin, 
                db_date_str
            )
            generated_id = f"{clean_isin}_{id_date_str}_{current_count:03d}"

            new_payload = {
                "username": st.session_state["user_name"],
                "id": generated_id,
                "account_code": account_selection.split(" (")[0],
                "isin": clean_isin,
                "date": db_date_str,
                "type_code": type_selection.split(" (")[0],
                "quantity": quantity,
                "total_amount_eur": amount_eur
            }
            
            try:
                save_transaction(new_payload)
                st.success(f"Transaction saved! ID: {generated_id}")
                st.cache_data.clear()
                st.session_state["view"] = "list"
                if 'ref_trans_loaded' in st.session_state: 
                    del st.session_state['ref_trans_loaded']
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save transaction: {e}")

