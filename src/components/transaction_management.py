import streamlit as st
import pandas as pd
import io
import uuid
import streamlit.components.v1 as components
from datetime import datetime
from src.utils import (
    extract_code, 
    apply_advanced_filters, 
    ensure_reference_data, 
    get_option_index
)
from src.database import (
    get_all_transactions, 
    get_ref_options, 
    get_asset_ref_options, 
    get_account_ref_options,
    save_transaction,
    save_transactions_bulk,
    get_next_transaction_count,
    get_existing_ids_for_bulk,
    get_import_settings,
    save_import_settings,
    get_missing_isins,
    save_asset_static_data
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
    st.subheader("Import Transactions via CSV")
    
    # --- NAVIGATION ROW AT TOP ---
    col_nav1, col_nav2, _ = st.columns([1, 2, 4])
    if col_nav1.button("⬅ Cancel", use_container_width=True):
        st.session_state["view"] = "list"
        st.rerun()

    # We only show the "Proceed" button if a file has been uploaded
    # It's now visible at the top once the CSV is ready
    proceed_placeholder = col_nav2.empty()

    st.write("Please select your CSV file and configure the format.")
    uploaded_file = st.file_uploader("Choose CSV file", type="csv")
    
    col1, col2 = st.columns(2)
    separator = col1.selectbox("Separator", options=[",", ";", "\t"], 
                               format_func=lambda x: "Comma" if x == "," else "Semicolon" if x == ";" else "Tab")
    decimal_sep = col2.selectbox("Decimal Separator", options=[",", "."], 
                                 format_func=lambda x: "Comma (,)" if x == "," else "Dot (.)")

    if uploaded_file is not None:
        try:
            thousand_sep = "." if decimal_sep == "," else ","
            df = pd.read_csv(uploaded_file, sep=separator, decimal=decimal_sep, thousands=thousand_sep)
            
            # Place the "Proceed" button in the placeholder created above
            if proceed_placeholder.button("Proceed with Mapping ➡", type="primary", use_container_width=True):
                df.insert(0, "import_row", True)
                st.session_state["imported_df"] = df
                st.session_state["view"] = "import_preview"
                if "scroll_done" in st.session_state: del st.session_state["scroll_done"]
                st.rerun()

            st.write("### Preview of uploaded data:")
            st.dataframe(df, use_container_width=True)
                
        except Exception as e:
            st.error(f"Error parsing CSV: {e}")



@st.dialog("Data Validation Error")
def show_validation_modal(error_count):
    st.warning(f"⚠️ {error_count} selected rows in your current view contain invalid data.")
    st.write("These rows have been automatically deselected. Please review the table before starting the import again.")
    if st.button("OK, I will review"):
        st.rerun()

def render_import_preview_screen():
    # --- 1. ROBUST AUTO-SCROLL TO TOP ---
    if "scroll_done" not in st.session_state:
        components.html(
            "<script>window.parent.window.scrollTo(0,0); var m = window.parent.document.querySelector('section.main'); if(m) m.scrollTo(0,0);</script>",
            height=0
        )
        st.session_state["scroll_done"] = True

    if "imported_df" not in st.session_state:
        st.session_state["view"] = "list"
        st.rerun()
        return

    # --- STATE INITIALIZATION ---
    if "val_error_indices" not in st.session_state: st.session_state["val_error_indices"] = []
    if "import_confirmed" not in st.session_state: st.session_state["import_confirmed"] = False
    if "import_filter_rules" not in st.session_state: st.session_state["import_filter_rules"] = []

    # --- REPLACEMENT: CENTRAL REFERENCE DATA LOADING ---
    # Ensures all required dropdown options (accounts, types, etc.) are in session_state
    ensure_reference_data()

    # --- VALIDATION GUARD ---
    if st.session_state["val_error_indices"]:
        err_indices = st.session_state["val_error_indices"]
        st.session_state["imported_df"].loc[err_indices, "import_row"] = False
        count = len(err_indices)
        st.session_state["val_error_indices"] = []
        show_validation_modal(count)

    df_raw = st.session_state["imported_df"]
    csv_columns = [c for c in df_raw.columns if c != "import_row"]
    user = st.session_state.get("user_id", "System")

    # --- NAVIGATION AT TOP ---
    if st.button("⬅ Back to Upload"):
        st.session_state["view"] = "import_upload"
        st.rerun()

    st.title("Finalize Import: Filter & Map")

    # --- SECTION 1: GLOBAL SETTINGS ---
    st.subheader("1. Global Settings")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        # Use centrally loaded account options
        accounts = st.session_state.get('opt_accounts', [])
        selected_account_full = st.selectbox("Target Account", accounts, key="active_account")
        # Optimized: Use helper to extract the account code
        acc_code = extract_code(selected_account_full)
    
    # --- INFO DISPLAY FOR LOADED SETTINGS ---
    raw_config = get_import_settings(user, acc_code)
    if raw_config:
        st.info(f"💡 Import settings loaded for account **{acc_code}**.")
        saved_config = raw_config
    else:
        st.warning(f"No previous settings found for **{acc_code}**. Please map fields manually.")
        saved_config = {}
    
    def get_map_idx(keyword, config_key):
        if config_key in saved_config:
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
        fc1, fc2 = st.columns([1, 4])
        if fc1.button("➕ Add Rule"):
            st.session_state["import_filter_rules"].append({"column": csv_columns[0], "value": []})
            st.rerun()
        if fc2.button("🗑 Clear All"):
            st.session_state["import_filter_rules"] = []
            st.rerun()

        active_filters = []
        for i, rule in enumerate(st.session_state["import_filter_rules"]):
            r1, r2, r3 = st.columns([2, 3, 0.5])
            sel_col = r1.selectbox(f"Col {i}", csv_columns, 
                                   index=csv_columns.index(rule["column"]) if rule["column"] in csv_columns else 0,
                                   key=f"fcol_{i}")
            st.session_state["import_filter_rules"][i]["column"] = sel_col
            opts = sorted(df_raw[sel_col].dropna().unique().astype(str).tolist())
            sel_val = r2.multiselect(f"Values {i}", opts, 
                                     default=rule["value"] if all(v in opts for v in rule["value"]) else [],
                                     key=f"fval_{i}")
            st.session_state["import_filter_rules"][i]["value"] = sel_val
            if sel_val: active_filters.append(df_raw[sel_col].astype(str).isin(sel_val))
            if r3.button("❌", key=f"frem_{i}"):
                st.session_state["import_filter_rules"].pop(i)
                st.rerun()

    filtered_df = df_raw.copy()
    if active_filters:
        mask = active_filters[0]
        for m in active_filters[1:]:
            mask = (mask & m) if logic_mode == "Match ALL (AND)" else (mask | m)
        filtered_df = df_raw[mask]

    # DATA EDITOR
    edited_df = st.data_editor(
        filtered_df,
        column_config={"import_row": st.column_config.CheckboxColumn("Import?", default=True)},
        disabled=csv_columns,
        hide_index=True, 
        use_container_width=True, 
        key="import_editor_final"
    )

    st.divider()

    # --- SECTION 3: TRANSACTION TYPE MAPPING ---
    st.subheader("3. Transaction Type Mapping")
    col_t1, _ = st.columns([1, 2])
    type_column = col_t1.selectbox("CSV Type Column", csv_columns, index=get_map_idx("type", "type_column"))
    
    distinct_csv_types = filtered_df[type_column].unique().tolist()
    # Optimized: Use centrally loaded transaction types
    db_trans_types = st.session_state.get('opt_trans_types', [])
    saved_type_map = saved_config.get("type_mapping", {})
    
    type_mapping = {}
    m_col1, m_col2 = st.columns(2)
    for i, csv_val in enumerate(distinct_csv_types):
        target_col = m_col1 if i % 2 == 0 else m_col2
        
        # Optimized: Use helper to find correct dropdown index
        d_idx = get_option_index(db_trans_types, saved_type_map.get(str(csv_val)))
        
        type_mapping[csv_val] = target_col.selectbox(
            f"CSV Type: '{csv_val}'", 
            db_trans_types, 
            index=d_idx, 
            key=f"tmap_{csv_val}"
        )

    st.divider()

    # --- SECTION 4: DATA FIELD MAPPING ---
    st.subheader("4. Data Field Mapping")
    st.markdown("Required Fields")
    with st.container(border=True):
        req_col1, req_col2 = st.columns(2)
        with req_col1:
            map_isin = st.selectbox("ISIN Column", csv_columns, index=get_map_idx("isin", "map_isin"))
            map_date = st.selectbox("Date Column", csv_columns, index=get_map_idx("date", "map_date"))
            map_qty  = st.selectbox("Quantity Column", csv_columns, index=get_map_idx("qty", "map_qty"))
        with req_col2:
            map_s_amt = st.selectbox("Settlement Amount", csv_columns, index=get_map_idx("amount", "map_settle_amt"))
            map_s_cur = st.selectbox("Settlement Currency", csv_columns, index=get_map_idx("curr", "map_settle_curr"))

    st.write("") 

    st.markdown("Optional Fields")    
    with st.container(border=True):        
        opt_col1, opt_col2 = st.columns(2)
        eur_opts = ["<Not in CSV>"] + csv_columns
        s_eur = saved_config.get("map_amt_eur", "<Not in CSV>")
        s_fx = saved_config.get("map_settle_fx", "<Not in CSV>")

        with opt_col1:
            map_eur = st.selectbox("Amount in EUR", eur_opts, 
                                   index=eur_opts.index(s_eur) if s_eur in eur_opts else 0)
        with opt_col2:
            map_fx = st.selectbox("FX Rate Column", eur_opts, 
                                  index=eur_opts.index(s_fx) if s_fx in eur_opts else 0)
        # INSERT VISIBLE HELP TEXT
        st.info("""
        **Priorities for currency conversion to EUR:** 

        1. **IF** Settlement Currency = EUR 
           **THEN** Amount in EUR := Settlement Amount and FX rate := 1.

        2. **IF** mapping for Amount in EUR is configured 
           **THEN** FX rate := Settlement Amount / Amount in EUR.

        3. **IF** mapping for FX rate is configured 
           **THEN** Amount in EUR := Settlement Amount / FX rate.

        4. **ELSE** Amount in EUR := NULL and FX rate := NULL.
        """)

    st.divider()

    # --- SECTION 5: DRY-RUN & EXECUTION ---
    if st.button("🚀 Start Import", type="primary", use_container_width=True):
        # Sync manual edits from the data editor
        if "import_editor_final" in st.session_state:
            edits = st.session_state["import_editor_final"].get("edited_rows", {})
            for ui_row_idx_str, change in edits.items():
                if "import_row" in change:
                    real_idx = filtered_df.index[int(ui_row_idx_str)]
                    st.session_state["imported_df"].at[real_idx, "import_row"] = change["import_row"]

        current_selection = st.session_state["imported_df"].loc[filtered_df.index]
        current_selection = current_selection[current_selection["import_row"] == True]
        
        if current_selection.empty:
            st.error("No rows selected in current filtered view.")
        else:
            invalid_indices = []
            for idx, row in current_selection.iterrows():
                try:
                    if pd.isna(row[map_date]) or str(row[map_date]).strip() == "": raise ValueError()
                    pd.to_datetime(row[map_date])
                    float(row[map_s_amt]); float(row[map_qty])
                    if pd.isna(row[map_isin]) or str(row[map_isin]).strip() == "": raise ValueError()
                except:
                    invalid_indices.append(idx)

            if invalid_indices:
                st.session_state["val_error_indices"] = invalid_indices
                st.rerun()
            else:
                st.session_state["import_confirmed"] = True
                st.rerun()

    # --- ACTUAL IMPORT PHASE ---
    if st.session_state.get("import_confirmed"):
        st.session_state["import_confirmed"] = False
        final_sel = st.session_state["imported_df"].loc[filtered_df.index]
        final_sel = final_sel[final_sel["import_row"] == True]
        
        # 1. ASSET PROVISIONING (Optimized JIT)
        unique_isins = [str(i).strip() for i in final_sel[map_isin].unique().tolist() if str(i).strip()]
        missing_isins = get_missing_isins(unique_isins)
        
        if missing_isins:
            with st.status(f"Provisioning {len(missing_isins)} new assets...") as status:
                asset_payloads = [{"isin": m_isin, "name": m_isin, "created_by": user} for m_isin in missing_isins]
                try:
                    save_asset_static_data(asset_payloads) 
                    st.write(f"✅ Created {len(asset_payloads)} assets.")
                except Exception as e:
                    if "duplicate" not in str(e).lower(): st.error(f"Asset provisioning error: {e}")
                status.update(label="Asset provisioning complete!", state="complete")

        # 2. PREPARE BATCH DATA
        success_count = 0
        progress_bar = st.progress(0)
        payload_batch = []
        unique_dates = [pd.to_datetime(d).date().isoformat() for d in final_sel[map_date].unique()]

        with st.status("Analyzing existing records and preparing batch...", expanded=True) as status:
            existing_ids = get_existing_ids_for_bulk(unique_isins, unique_dates)
            local_counters = {}
            for eid in existing_ids:
                try:
                    parts = eid.split("_")
                    if len(parts) >= 3:
                        isin_part, date_part, count_val = parts[0], parts[1], int(parts[2])
                        db_date_fmt = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"
                        key = (isin_part, db_date_fmt)
                        local_counters[key] = max(local_counters.get(key, 0), count_val + 1)
                except: continue

            for i, (idx, row) in enumerate(final_sel.iterrows()):
                try:
                    s_curr = str(row[map_s_cur]).upper().strip()[:3]
                    s_amount = float(row[map_s_amt])
                    raw_date = pd.to_datetime(row[map_date])
                    db_date = raw_date.date().isoformat()
                    isin_val = str(row[map_isin]).strip()

                    # Currency logic
                    amt_eur = None
                    if s_curr == "EUR": amt_eur = s_amount
                    elif map_eur != "<Not in CSV>" and pd.notna(row[map_eur]): amt_eur = float(row[map_eur])
                    elif map_fx != "<Not in CSV>" and pd.notna(row[map_fx]) and float(row[map_fx]) != 0:
                        amt_eur = s_amount / float(row[map_fx])

                    settle_fx = None
                    if s_curr == "EUR": settle_fx = 1.0
                    elif map_eur != "<Not in CSV>" and pd.notna(row[map_eur]) and float(row[map_eur]) != 0:
                        settle_fx = s_amount / float(row[map_eur])
                    elif map_fx != "<Not in CSV>" and pd.notna(row[map_fx]): settle_fx = float(row[map_fx])

                    # Optimized ID Generation
                    key = (isin_val, db_date)
                    current_idx = local_counters.get(key, 0)
                    generated_id = f"{isin_val}_{raw_date.strftime('%Y%m%d')}_{current_idx:03d}"
                    local_counters[key] = current_idx + 1

                    # Optimized: Use extract_code helper for type mapping
                    payload_batch.append({
                        "user_id": user_id,
                        "id": generated_id,
                        "account_code": acc_code,
                        "isin": isin_val,
                        "date": db_date,
                        "type_code": extract_code(type_mapping[row[type_column]]),
                        "quantity": float(row[map_qty]),
                        "settle_amount": s_amount,
                        "settle_currency": s_curr,
                        "settle_fxrate": settle_fx,
                        "amount_eur": amt_eur
                    })
                except Exception as e:
                    st.error(f"Row {idx} calculation error: {e}")
                
                if i % 10 == 0 or i == len(final_sel)-1: progress_bar.progress((i + 1) / len(final_sel))

            # 3. EXECUTE BULK INSERT
            if payload_batch:
                status.update(label=f"Uploading {len(payload_batch)} records...", state="running")
                try:
                    save_transactions_bulk(payload_batch)
                    success_count = len(payload_batch)
                    status.update(label=f"Successfully imported {success_count} transactions!", state="complete")
                except Exception as e:
                    st.error(f"Database Error: {e}")
                    status.update(label="Import failed.", state="error")

        # 4. FINALIZE & SAVE SETTINGS
        save_import_settings(user, acc_code, {
            "type_column": type_column, "type_mapping": type_mapping,
            "map_isin": map_isin, "map_date": map_date, "map_qty": map_qty,
            "map_settle_amt": map_s_amt, "map_settle_curr": map_s_cur, 
            "map_amt_eur": map_eur, "map_settle_fx": map_fx
        })
        
        st.success(f"Import complete: {success_count} transactions saved.")
        st.cache_data.clear()
        if "imported_df" in st.session_state: del st.session_state["imported_df"]
        if "scroll_done" in st.session_state: del st.session_state["scroll_done"]
        st.session_state["view"] = "list"
        st.rerun()


def render_list_view():
    """
    Displays the transaction table with advanced filtering and formatted columns.
    Uses centralized utility functions for filtering and state management.
    """
    st.title("Transactions")
    
    # --- 1. NAVIGATION & ACTION BUTTONS ---
    col_btn1, col_btn2, _ = st.columns([1, 1, 4])
    with col_btn1:
        if st.button("➕ New Transaction", use_container_width=True):
            st.session_state["view"] = "form"
            st.rerun()
    with col_btn2:
        if st.button("📥 Import CSV", use_container_width=True):
            # Clear scroll state to ensure the import screen starts at the top
            if "scroll_done" in st.session_state: 
                del st.session_state["scroll_done"]
            st.session_state["view"] = "import_upload"
            st.rerun()

    # --- 2. DATA RETRIEVAL ---
    data = get_all_transactions()
    if not data:
        st.info("No records found in transactions.")
        return

    # Convert Supabase response to DataFrame
    df = pd.DataFrame(data)
    
    # --- 3. ADVANCED FILTERING ---
    # apply_advanced_filters handles date conversion and multi-rule logic
    filtered_df = apply_advanced_filters(df, session_prefix="trans_list")

    # --- 4. DATA PROCESSING & SORTING ---
    # Ensure created_at is datetime for accurate chronological sorting
    if 'created_at' in filtered_df.columns:
        filtered_df['created_at'] = pd.to_datetime(filtered_df['created_at'])
        # Default Sort: Show most recently created records first
        filtered_df = filtered_df.sort_values(by='created_at', ascending=False)

    # --- 5. COLUMN ORDERING & DISPLAY ---
    # Define a logical sequence for the columns to be displayed
    preferred_order = [
        "date", "account_code", "isin", "type_code", 
        "quantity", "settle_amount", "settle_currency", 
        "settle_fxrate", "amount_eur",
        "created_at", "updated_at", "id"
    ]
    
    # Filter preferred_order to only include columns that actually exist in the dataframe
    existing_cols = [c for c in preferred_order if c in filtered_df.columns]
    display_df = filtered_df[existing_cols]

    st.write(f"Showing **{len(display_df)}** transactions.")
    
    # Render the main data table with specific column configurations
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "date": st.column_config.DateColumn("Trade Date", format="DD.MM.YYYY"),
            "account_code": st.column_config.TextColumn("Account"),
            "isin": st.column_config.TextColumn("ISIN"),
            "type_code": st.column_config.TextColumn("Type"),
            "quantity": st.column_config.NumberColumn("Quantity", format="%.4f"),
            "settle_amount": st.column_config.NumberColumn("Settle Amount", format="%.2f"),
            "settle_currency": st.column_config.TextColumn("Curr"),
            "settle_fxrate": st.column_config.NumberColumn("FX Rate", format="%.6f"),
            "amount_eur": st.column_config.NumberColumn("Amount (EUR)", format="%.2f"),
            "created_at": st.column_config.DatetimeColumn("Created At", format="DD.MM.YYYY, HH:mm"),
            "updated_at": st.column_config.DatetimeColumn("Updated At", format="DD.MM.YYYY, HH:mm"),
            "id": st.column_config.TextColumn("Internal ID"),
        }
    )



def render_transaction_form():
    """Renders an improved transaction form with dynamic FX-Rate locking."""
    st.subheader("Create New Transaction")
    
    # Navigation back to the list view
    if st.button("⬅ Cancel"):
        st.session_state["view"] = "list"
        st.rerun()

    # --- REPLACEMENT: CENTRAL REFERENCE DATA LOADING ---
    # This replaces the manual 'if ref_trans_loaded not in st.session_state' block
    # It ensures all required dropdown options are available in st.session_state
    ensure_reference_data()

    # Local UI options for currency
    currency_options = ["EUR", "USD", "CHF", "GBP", "JPY", "CAD"]

    # --- DYNAMIC FX SECTION ---
    # Placed outside the form to allow immediate UI updates when currency changes
    col_top1, col_top2 = st.columns(2)
    with col_top1:
        s_curr = st.selectbox("Settlement Currency", currency_options, index=0)
    
    # Logic for locking the FX rate field
    is_eur = (s_curr == "EUR")
    
    with col_top2:
        # If EUR, the value is forced to 1.0 and the field is disabled
        s_fx = st.number_input(
            "FX Rate (Settle/EUR)", 
            step=0.000001, 
            format="%.6f", 
            value=1.0 if is_eur else st.session_state.get("last_fx", 0.0),
            disabled=is_eur,
            help="Locked to 1.0 for EUR transactions." if is_eur else "Enter rate: 1 unit of foreign currency = X units of EUR"
        )
        # Store non-EUR rate in session state to preserve it during UI reruns
        if not is_eur:
            st.session_state["last_fx"] = s_fx

    # --- MAIN TRANSACTION FORM ---
    with st.form("transaction_main_data"):
        col1, col2 = st.columns(2)
        
        # Using the options loaded by ensure_reference_data()
        account_selection = col1.selectbox("Account", st.session_state.get('opt_accounts', []))
        asset_selection = col2.selectbox("Asset (ISIN)", st.session_state.get('opt_assets', []))
        
        type_selection = col1.selectbox("Transaction Type", st.session_state.get('opt_trans_types', []))
        trans_date = col2.date_input("Transaction Date", value=datetime.now())
        
        quantity = col1.number_input("Quantity", step=0.0001, format="%.4f", min_value=0.0)
        s_amount = col2.number_input("Settlement Amount", step=0.01, format="%.2f", min_value=0.0)
        
        st.divider()
        submit = st.form_submit_button("Save Transaction", type="primary", use_container_width=True)

        if submit:
            # Validation: FX Rate must be greater than 0 for non-EUR currencies
            if not is_eur and s_fx <= 0:
                st.error("Please enter a valid FX Rate for foreign currency transactions.")
                st.stop()

            # Calculate the EUR equivalent
            calc_eur = s_amount if is_eur else (s_amount / s_fx if s_fx > 0 else 0.0)
            
            # Use the 'extract_code' helper to get clean IDs from selection strings
            clean_isin = extract_code(asset_selection) if asset_selection else ""
            db_date_str = trans_date.isoformat()
            
            # Generate the unique transaction ID
            current_count = get_next_transaction_count(
                st.session_state["user_id"], 
                clean_isin, 
                db_date_str
            )
            generated_id = f"{clean_isin}_{trans_date.strftime('%Y%m%d')}_{current_count:03d}"

            # Construct the database payload
            new_payload = {
                "user_id": st.session_state["user_id"],
                "id": generated_id,
                "account_code": extract_code(account_selection),
                "isin": clean_isin,
                "date": db_date_str,
                "type_code": extract_code(type_selection),
                "quantity": quantity,
                "settle_amount": s_amount,
                "settle_currency": s_curr,
                "settle_fxrate": 1.0 if is_eur else s_fx,
                "amount_eur": calc_eur
            }
            
            try:
                # Save to database and cleanup
                save_transaction(new_payload)
                st.success(f"Transaction saved successfully! (EUR {calc_eur:.2f})")
                st.cache_data.clear()
                st.session_state["view"] = "list"
                st.rerun()
            except Exception as e:
                st.error(f"Database Error: {e}")






