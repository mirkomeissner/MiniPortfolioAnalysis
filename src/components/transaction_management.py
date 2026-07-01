import streamlit as st
import pandas as pd
import io
import uuid
import streamlit.components.v1 as components
from datetime import datetime
from src.utils import (
    apply_advanced_filters,
    create_assets_bulk_via_backend,
    create_transaction_via_backend,
    delete_all_transactions_via_backend,
    ensure_reference_data,
    extract_code,
    fetch_transactions_df,
    get_asset_price_start_date_via_backend,
    get_asset_price_start_dates_via_backend,
    get_existing_ids_for_bulk_via_backend,
    get_holdings_reorganization_status_via_backend,
    get_import_settings_via_backend,
    get_missing_isins_via_backend,
    get_next_transaction_count_via_backend,
    get_option_index,
    reorganize_holdings_via_backend,
    save_import_settings_via_backend,
    save_transactions_bulk_via_backend,
    update_asset_start_dates_bulk_via_backend,
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


def _format_status_timestamp(timestamp):
    if timestamp is None:
        return "n/a"
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def _get_holdings_reorganization_ui_state(status):
    last_transaction_modification = status["last_transaction_modification"] if status else None
    last_reorganization = status["last_reorganization"] if status else None

    if last_transaction_modification is None:
        return {
            "visible": False,
            "label": None,
            "disabled": False,
            "info_text": None,
        }

    if last_reorganization is None:
        return {
            "visible": True,
            "label": "Reorganization of Holdings",
            "disabled": False,
            "info_text": "",
        }

    holdings_are_up_to_date = last_reorganization > last_transaction_modification
    return {
        "visible": True,
        "label": "holdings are up to date" if holdings_are_up_to_date else "Reorganization of Holdings",
        "disabled": holdings_are_up_to_date,
        "info_text": (
            f"Last modification of transactions was at {_format_status_timestamp(last_transaction_modification)} "
            f"and last reorganization was at {_format_status_timestamp(last_reorganization)}"
        ),
    }


def _render_holdings_reorganization_controls():
    user_id = st.session_state.get("user_id")
    status = get_holdings_reorganization_status_via_backend(user_id)
    ui_state = _get_holdings_reorganization_ui_state(status)

    if not ui_state["visible"]:
        return

    button_col, info_col = st.columns([1, 3])
    with button_col:
        if st.button(ui_state["label"], disabled=ui_state["disabled"]):
            try:
                summary = reorganize_holdings_via_backend(user_id=user_id)
                relevant_accounts_count = summary.get("relevant_accounts_count", 0)
                if relevant_accounts_count == 0:
                    st.info("No account requires holdings reorganization.")
                else:
                    st.success(
                        "Holdings reorganization completed "
                        f"(accounts={relevant_accounts_count}, "
                        f"inserted={summary.get('rows_inserted', 0)}, "
                        f"updated={summary.get('rows_updated', 0)}, "
                        f"deleted={summary.get('rows_deleted', 0)})."
                    )
                st.rerun()
            except Exception as exc:
                st.error(f"Could not reorganize holdings: {exc}")

    with info_col:
        if ui_state["info_text"]:
            st.write(ui_state["info_text"])

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
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("No valid User-ID found. Please log in again.")
        st.stop()

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
    raw_config = get_import_settings_via_backend(user_id, acc_code)
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
    
    filtered_df = apply_advanced_filters(df_raw, session_prefix="import_preview")
    
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

    # --- SMART INVERSION LOGIC ---
    st.subheader("5. Smart Data Processing")
    st.markdown("Automated value adjustment based on transaction direction.")
    
    with st.container(border=True):
        col_smart1, col_smart2 = st.columns([3, 1])
        with col_smart1:
            st.write("**Auto-Invert Outflows**")
            st.caption("""
                If enabled, the system checks the transaction type. If it is a **'Sell'** or **'Transfer Out'**, 
                Quantity and all Amounts will be forced to negative values (inverted if positive in CSV).
            """)
        with col_smart2:
            # We load the previous setting if available, default to True
            s_invert = saved_config.get("smart_invert", True)
            smart_invert = st.checkbox("Enable Inversion", value=s_invert, key="smart_invert_toggle")

    
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
        missing_isins = get_missing_isins_via_backend(unique_isins)
        
        if missing_isins:
            with st.status(f"Provisioning {len(missing_isins)} new assets...") as status:
                # Pre-calculate the earliest transaction date per ISIN so new assets can be created
                # with the correct price_start_date immediately.
                min_dates = {}
                for isin_val in missing_isins:
                    relevant_dates = pd.to_datetime(final_sel.loc[final_sel[map_isin].astype(str).str.strip() == isin_val, map_date])
                    if relevant_dates.empty:
                        continue
                    min_dates[isin_val] = relevant_dates.min().date().isoformat()

                now_ts = datetime.now().isoformat()
                asset_payloads = []
                for m_isin in missing_isins:
                    payload = {
                        "isin": m_isin,
                        "name": m_isin,
                        "created_at": now_ts,
                        "updated_at": None,
                        "created_by": user_id,
                        "updated_by": None
                    }
                    if m_isin in min_dates:
                        payload["price_start_date"] = min_dates[m_isin]
                    asset_payloads.append(payload)

                try:
                    create_assets_bulk_via_backend(asset_payloads)
                except Exception as e:
                    if "duplicate" not in str(e).lower(): st.error(f"Asset provisioning error: {e}")
                status.update(label="Asset provisioning complete!", state="complete")

        # 2. PREPARE BATCH DATA
        success_count = 0
        progress_bar = st.progress(0)
        payload_batch = []
        unique_dates = [pd.to_datetime(d).date().isoformat() for d in final_sel[map_date].unique()]

        with st.status("Analyzing existing records and preparing batch...", expanded=True) as status:
            existing_ids = get_existing_ids_for_bulk_via_backend(user_id, unique_isins, unique_dates)
            local_counters = {}
            for eid in existing_ids:
                try:
                    parts = eid.split("_")
                    if len(parts) >= 3:
                        key = (parts[0], f"{parts[1][:4]}-{parts[1][4:6]}-{parts[1][6:]}")
                        local_counters[key] = max(local_counters.get(key, 0), int(parts[2]) + 1)
                except: continue

            for i, (idx, row) in enumerate(final_sel.iterrows()):
                try:
                    # Basic extraction from CSV
                    s_curr = str(row[map_s_cur]).upper().strip()[:3]
                    raw_qty = float(row[map_qty])
                    raw_amt = float(row[map_s_amt])
                    db_date = pd.to_datetime(row[map_date]).date().isoformat()
                    isin_val = str(row[map_isin]).strip()

                    # Get transaction type code
                    type_label_full = type_mapping[row[type_column]]
                    transaction_type_code = extract_code(type_label_full)
                    
                    # Fetch logic rules from session state (loaded from shared.ref_transaction_logic)
                    logic = st.session_state.get("type_logic_map", {}).get(transaction_type_code, {})
                    q_logic = logic.get("quantity_sign") # 1, -1, 0, or None
                    a_logic = logic.get("amount_sign")   # 1, -1, 0, or None

                    # --- APPLY SMART DIRECTION LOGIC (if enabled) ---
                    if smart_invert:
                        # Quantity Logic: 1=Positive, -1=Negative, 0=NULL, None=As Is
                        if q_logic == 1:      qty = abs(raw_qty)
                        elif q_logic == -1:   qty = -abs(raw_qty)
                        elif q_logic == 0:    qty = None
                        else:                 qty = raw_qty
                        
                        # Amount Logic: 1=Positive, -1=Negative, 0=NULL, None=As Is
                        if a_logic == 1:      
                            s_amount = abs(raw_amt)
                        elif a_logic == -1:   
                            s_amount = -abs(raw_amt)
                        elif a_logic == 0:    
                            s_amount = None                  
                            s_curr = None
                        else:                 
                            s_amount = raw_amt
                    else:
                        qty = raw_qty
                        s_amount = raw_amt

                    # --- CURRENCY & EUR CALCULATION ---
                    amt_eur = None
                    settle_fx = None
                    
                    # Calculation only proceeds if s_amount is not None
                    if s_amount is not None:
                        if s_curr == "EUR":
                            amt_eur = s_amount
                            settle_fx = 1.0
                        else:
                            # 1. Check for manual EUR column in CSV
                            if map_eur != "<Not in CSV>" and pd.notna(row[map_eur]):
                                val_eur = abs(float(row[map_eur]))
                                amt_eur = -val_eur if s_amount < 0 else val_eur
                            # 2. Fallback to FX Rate column
                            elif map_fx != "<Not in CSV>" and pd.notna(row[map_fx]) and float(row[map_fx]) != 0:
                                amt_eur = s_amount / float(row[map_fx])
                            
                            # Derive FX rate
                            if amt_eur and amt_eur != 0:
                                settle_fx = abs(s_amount / amt_eur)
                            elif map_fx != "<Not in CSV>" and pd.notna(row[map_fx]):
                                settle_fx = float(row[map_fx])

                    # ID Generation Logic
                    key = (isin_val, db_date)
                    current_idx = local_counters.get(key, 0)
                    generated_id = f"{isin_val}_{db_date.replace('-','')}_{current_idx:03d}"
                    local_counters[key] = current_idx + 1

                    payload_batch.append({
                        "user_id": user_id,
                        "id": generated_id,
                        "account_code": acc_code,
                        "isin": isin_val,
                        "date": db_date,
                        "transaction_type_code": transaction_type_code,
                        "quantity": qty,
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
                try:
                    save_transactions_bulk_via_backend(payload_batch)
                    success_count = len(payload_batch)
                except Exception as e:
                    st.error(f"Database Error: {e}")

                # 3a. Update price_start_date for imported ISINs in one bulk DB request
                price_start_map = get_asset_price_start_dates_via_backend(unique_isins)
                bulk_price_start_updates = []
                for isin_val in unique_isins:
                    try:
                        relevant_dates = pd.to_datetime(final_sel.loc[final_sel[map_isin].astype(str).str.strip() == isin_val, map_date])
                        if relevant_dates.empty:
                            continue
                        earliest_date = relevant_dates.min().date().isoformat()
                        current_start = price_start_map.get(isin_val)
                        if current_start is None or earliest_date < current_start:
                            bulk_price_start_updates.append({
                                "isin": isin_val,
                                "price_start_date": earliest_date
                            })
                    except Exception:
                        continue

                if bulk_price_start_updates:
                    update_asset_start_dates_bulk_via_backend(bulk_price_start_updates)

        # 4. FINALIZE & SAVE SETTINGS
        save_import_settings_via_backend(user_id, acc_code, {
            "type_column": type_column, "type_mapping": type_mapping,
            "map_isin": map_isin, "map_date": map_date, "map_qty": map_qty,
            "map_settle_amt": map_s_amt, "map_settle_curr": map_s_cur, 
            "map_amt_eur": map_eur, "map_settle_fx": map_fx,
            "smart_invert": smart_invert
        })
        
        st.success(f"Import complete: {success_count} transactions saved.")
        st.cache_data.clear()
        if "imported_df" in st.session_state: del st.session_state["imported_df"]
        if "scroll_done" in st.session_state: del st.session_state["scroll_done"]
        st.session_state["view"] = "list"
        st.rerun()




@st.dialog("Delete All Transactions - Confirm")
def confirm_delete_all_first():
    """First confirmation dialog for deleting all transactions"""
    st.warning("⚠️ This action will permanently delete **all transactions and all positions (holdings)** across **all your accounts**.")
    st.write("This cannot be undone.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state["delete_all_confirmed_first"] = False
            st.rerun()
    with col2:
        if st.button("⚠️ I understand, continue", use_container_width=True, type="secondary"):
            st.session_state["delete_all_confirmed_first"] = True
            st.rerun()


@st.dialog("Delete All Transactions - Final Confirmation")
def confirm_delete_all_final():
    """Second confirmation dialog for deleting all transactions"""
    st.error("🚨 FINAL WARNING: All transactions and all positions (holdings) in all your accounts will be permanently deleted!")
    st.write("Please confirm one more time.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state["delete_all_confirmed_first"] = False
            st.session_state["delete_all_confirmed_final"] = False
            st.rerun()
    with col2:
        if st.button("🗑️ Yes, delete all transactions", use_container_width=True, type="primary"):
            st.session_state["delete_all_confirmed_final"] = True
            st.rerun()


def render_list_view():
    """
    Displays the transaction table with advanced filtering and formatted columns.
    Uses centralized utility functions for filtering and state management.
    """
    st.title("Transactions")
    
    # --- 1. NAVIGATION & ACTION BUTTONS ---
    col_btn1, col_btn2, col_btn3, _ = st.columns([1, 1, 1, 3])
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
    with col_btn3:
        if st.button("🗑️ Delete All", use_container_width=True):
            st.session_state["delete_all_confirmed_first"] = False
            st.session_state["delete_all_confirmed_final"] = False
            confirm_delete_all_first()
    
    # Handle the deletion process
    if st.session_state.get("delete_all_confirmed_first") and not st.session_state.get("delete_all_confirmed_final"):
        confirm_delete_all_final()
    
    if st.session_state.get("delete_all_confirmed_final"):
        try:
            delete_all_transactions_via_backend(st.session_state["user_id"])
            st.session_state["delete_all_confirmed_first"] = False
            st.session_state["delete_all_confirmed_final"] = False
            st.success("✅ All transactions and positions (holdings) have been deleted successfully across all your accounts!")
            st.rerun()
        except Exception as e:
            st.error(f"Error deleting transactions: {e}")
            st.session_state["delete_all_confirmed_first"] = False
            st.session_state["delete_all_confirmed_final"] = False

    # Holdings reorganization controls are shown below action buttons and above the table.
    _render_holdings_reorganization_controls()

    # --- 2. DATA RETRIEVAL ---
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("No valid User-ID found. Please log in again.")
        return

    df = fetch_transactions_df(user_id)
    if df.empty:
        st.info("No records found in transactions.")
        return

    # --- 4. ADVANCED FILTERING ---
    # Jetzt sieht der Query Builder automatisch "Trade Date", "Account", etc.
    filtered_df = apply_advanced_filters(df, session_prefix="trans_list")

    # --- 5. DATA DISPLAY ---
    st.write(f"Showing **{len(filtered_df)}** transactions.")
    
    # Da die Spalten schon umbenannt sind, brauchen wir in der column_config 
    # nur noch die Formatierungen (Zahlen/Daten), aber keine Labels mehr.
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Trade Date": st.column_config.DateColumn(format="DD.MM.YYYY"),
            "Quantity": st.column_config.NumberColumn(format="%.4f"),
            "Settle Amount": st.column_config.NumberColumn(format="%.2f"),
            "FX Rate": st.column_config.NumberColumn(format="%.6f"),
            "Amount (EUR)": st.column_config.NumberColumn(format="%.2f"),
            "Created At": st.column_config.DatetimeColumn(format="DD.MM.YYYY, HH:mm"),
            "Updated At": st.column_config.DatetimeColumn(format="DD.MM.YYYY, HH:mm"),
        }
    )

def render_transaction_form():
    """Renders an improved transaction form with dynamic FX-Rate locking."""
    # --- REPLACEMENT: CENTRAL REFERENCE DATA LOADING ---
    # This replaces the manual 'if ref_trans_loaded not in st.session_state' block
    # It ensures all required dropdown options are available in st.session_state
    ensure_reference_data()

    st.subheader("Create New Transaction")
    
    # Navigation back to the list view
    if st.button("⬅ Cancel"):
        st.session_state["view"] = "list"
        st.rerun()

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
        
        quantity = col1.number_input("Quantity", step=0.0001, format="%.4f")
        s_amount = col2.number_input("Settlement Amount", step=0.01, format="%.2f")
        
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
            current_count = get_next_transaction_count_via_backend(
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
                "transaction_type_code": extract_code(type_selection),
                "quantity": quantity,
                "settle_amount": s_amount,
                "settle_currency": s_curr,
                "settle_fxrate": 1.0 if is_eur else s_fx,
                "amount_eur": calc_eur
            }
            
            try:
                # Save to database and cleanup
                create_transaction_via_backend(new_payload)

                # Update asset price start date if transaction is earlier than current stored start date
                current_start = get_asset_price_start_date_via_backend(clean_isin)
                if current_start is None or db_date_str < current_start:
                    update_asset_start_dates_bulk_via_backend([
                        {"isin": clean_isin, "price_start_date": db_date_str}
                    ])

                st.success(f"Transaction saved successfully! (EUR {calc_eur:.2f})")
                st.cache_data.clear()
                st.session_state["view"] = "list"
                st.rerun()
            except Exception as e:
                st.error(f"Database Error: {e}")






