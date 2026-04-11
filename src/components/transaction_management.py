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
    get_next_transaction_count,
    get_import_settings,
    save_import_settings
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
            
            if st.button("Proceed with Mapping", type="primary"):
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
    Import Preview Screen with:
    1. Validation Guard: Deselects faulty rows before rendering UI.
    2. Persistent Mapping: Loads/Saves user settings per account.
    3. Advanced Filtering: AND/OR logic for CSV exploration.
    4. Safe Execution: Only imports when 100% of selection is valid.
    """
    st.title("Finalize Import: Filter & Map")

    if "imported_df" not in st.session_state:
        st.session_state["view"] = "list"
        st.rerun()
        return

    # --- VALIDATION GUARD ---
    # If the previous run detected errors, we apply the deselection here
    # before any UI elements are rendered.
    if "val_error_indices" in st.session_state and st.session_state["val_error_indices"]:
        err_idx = st.session_state["val_error_indices"]
        # Update the source dataframe: uncheck the broken rows
        st.session_state["imported_df"].loc[err_idx, "import_row"] = False
        # Clear the error state to prevent infinite loops
        st.session_state["val_error_indices"] = []
        st.warning(f"⚠️ {len(err_idx)} rows contained errors and were deselected. Please review the selection.")
        # No rerun needed here, we just continue to render with updated data

    # Configuration and setup
    df_raw = st.session_state["imported_df"]
    csv_columns = df_raw.columns.tolist()
    user = st.session_state.get("user_name", "System")

    # --- SECTION 1: GLOBAL SETTINGS & PERSISTENCE ---
    st.subheader("1. Global Settings")
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        accounts = get_account_ref_options(user)
        selected_account_full = st.selectbox("Target Account", accounts, key="active_account")
        acc_code = selected_account_full.split(" (")[0]

    # Load persistent mapping
    saved_config = get_import_settings(user, acc_code)
    
    def get_map_idx(keyword, config_key):
        if saved_config and config_key in saved_config:
            val = saved_config[config_key]
            if val in csv_columns: return csv_columns.index(val)
        for i, col in enumerate(csv_columns):
            if keyword.lower() in col.lower(): return i
        return 0

    st.divider()

    # --- SECTION 2: ADVANCED FILTERING ---
    st.subheader("2. Filter Rows")
    with st.expander("🛠 Advanced Query Builder", expanded=False):
        logic_mode = st.radio("Logic Mode", ["Match ALL (AND)", "Match ANY (OR)"], horizontal=True)
        if "import_filter_rules" not in st.session_state:
            st.session_state["import_filter_rules"] = []
        
        fc1, fc2 = st.columns([1, 4])
        if fc1.button("➕ Add Rule"):
            st.session_state["import_filter_rules"].append({"column": csv_columns[0], "value": None})
            st.rerun()
        if fc2.button("🗑 Clear All"):
            st.session_state["import_filter_rules"] = []
            st.rerun()

        active_filters = []
        for i, rule in enumerate(st.session_state["import_filter_rules"]):
            r1, r2, r3 = st.columns([2, 3, 0.5])
            col_name = r1.selectbox(f"Col {i}", csv_columns, key=f"fcol_{i}")
            opts = sorted(df_raw[col_name].dropna().unique().astype(str).tolist())
            val = r2.multiselect(f"Values {i}", opts, key=f"fval_{i}")
            if val: active_filters.append(df_raw[col_name].astype(str).isin(val))
            if r3.button("❌", key=f"frem_{i}"):
                st.session_state["import_filter_rules"].pop(i)
                st.rerun()

    # Apply filtering for the view
    filtered_df = df_raw.copy()
    if active_filters:
        mask = active_filters[0]
        for m in active_filters[1:]:
            mask = (mask & m) if logic_mode == "Match ALL (AND)" else (mask | m)
        filtered_df = df_raw[mask]

    # Render the interactive Data Editor
    edited_df = st.data_editor(
        filtered_df,
        column_config={"import_row": st.column_config.CheckboxColumn("Import?", default=True)},
        disabled=[c for c in filtered_df.columns if c != "import_row"],
        hide_index=True,
        use_container_width=True,
        key="import_editor_final"
    )

    st.divider()

    # --- SECTION 3: TYPE MAPPING ---
    st.subheader("3. Transaction Type Mapping")
    col_t1, _ = st.columns([1, 2])
    type_column = col_t1.selectbox("CSV Type Column", csv_columns, index=get_map_idx("type", "type_column"))
    
    distinct_csv_types = filtered_df[type_column].unique().tolist()
    db_trans_types = get_ref_options("ref_transaction_type")
    saved_type_map = saved_config.get("type_mapping", {}) if saved_config else {}
    
    type_mapping = {}
    m_col1, m_col2 = st.columns(2)
    for i, csv_val in enumerate(distinct_csv_types):
        target_col = m_col1 if i % 2 == 0 else m_col2
        default_idx = 0
        if csv_val in saved_type_map and saved_type_map[csv_val] in db_trans_types:
            default_idx = db_trans_types.index(saved_type_map[csv_val])
        
        type_mapping[csv_val] = target_col.selectbox(f"CSV: '{csv_val}'", options=db_trans_types, 
                                                     index=default_idx, key=f"tmap_{csv_val}")

    st.divider()

    # --- SECTION 4: FIELD MAPPING ---
    st.subheader("4. Data Field Mapping")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        map_isin = st.selectbox("ISIN Column", csv_columns, index=get_map_idx("isin", "map_isin"))
        map_date = st.selectbox("Date Column", csv_columns, index=get_map_idx("date", "map_date"))
        map_qty  = st.selectbox("Quantity Column", csv_columns, index=get_map_idx("qty", "map_qty"))
    with col_m2:
        map_trade_amt = st.selectbox("Trade Amount", csv_columns, index=get_map_idx("amount", "map_trade_amt"))
        map_trade_curr = st.selectbox("Trade Currency", csv_columns, index=get_map_idx("curr", "map_trade_curr"))
        eur_opts = ["<Not in CSV>"] + csv_columns
        saved_eur = saved_config.get("map_amt_eur", "<Not in CSV>") if saved_config else "<Not in CSV>"
        map_amt_eur = st.selectbox("Amount in EUR (Optional)", eur_opts, 
                                   index=eur_opts.index(saved_eur) if saved_eur in eur_opts else 0)

    st.divider()

    # --- SECTION 5: VALIDATION & EXECUTION ---
    if st.button("🚀 Start Import", type="primary", use_container_width=True):
        # 1. Capture current UI selection
        current_selection = edited_df[edited_df["import_row"] == True].copy()
        
        if current_selection.empty:
            st.error("No rows selected.")
            return

        # 2. DRY-RUN VALIDATION
        invalid_indices = []
        for idx, row in current_selection.iterrows():
            try:
                # Test formats
                pd.to_datetime(row[map_date])
                float(row[map_trade_amt])
                float(row[map_qty])
                if pd.isna(row[map_isin]) or str(row[map_isin]).strip() == "":
                    raise ValueError("Missing ISIN")
            except:
                invalid_indices.append(idx)

        # 3. HANDLE ERRORS
        if invalid_indices:
            # Trigger the Guard: Save indices and Rerun
            st.session_state["val_error_indices"] = invalid_indices
            st.rerun()
            return

        # 4. EXECUTE IMPORT
        success_count = 0
        progress_bar = st.progress(0)
        
        for i, (idx, row) in enumerate(current_selection.iterrows()):
            try:
                t_curr = str(row[map_trade_curr]).upper().strip()[:3]
                t_amount = float(row[map_trade_amt])
                raw_date = pd.to_datetime(row[map_date])
                db_date = raw_date.date().isoformat()
                clean_isin = str(row[map_isin]).strip()
                
                payload = {
                    "username": user,
                    "id": f"{clean_isin}_{raw_date.strftime('%Y%m%d')}_{get_next_transaction_count(user, clean_isin, db_date):03d}",
                    "account_code": acc_code,
                    "isin": clean_isin,
                    "date": db_date,
                    "type_code": type_mapping[row[type_column]].split(" (")[0],
                    "quantity": float(row[map_qty]),
                    "trade_amount": t_amount,
                    "trade_currency": t_curr,
                    "amount_eur": t_amount if t_curr == "EUR" else (float(row[map_amt_eur]) if map_amt_eur != "<Not in CSV>" else None)
                }
                save_transaction(payload)
                success_count += 1
            except Exception as e:
                st.error(f"Critical error in row {idx}: {e}")
            progress_bar.progress((i + 1) / len(current_selection))

        # 5. POST-IMPORT CLEANUP
        save_import_settings(user, acc_code, {
            "type_column": type_column, "type_mapping": type_mapping,
            "map_isin": map_isin, "map_date": map_date, "map_qty": map_qty,
            "map_trade_amt": map_trade_amt, "map_trade_curr": map_trade_curr, "map_amt_eur": map_amt_eur
        })
        
        st.success(f"Success! {success_count} transactions imported.")
        st.cache_data.clear()
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

