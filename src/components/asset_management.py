import streamlit as st
import pandas as pd
from datetime import datetime
from src.database import (
    get_all_assets_with_labels, 
    update_asset_static_data, 
    get_ref_options
)
from .ticker_search import ticker_search_view

def asset_table_view():
    # --- VIEW ROUTING ---
    current_view = st.session_state.get("view", "list")

    if current_view == "search":
        if st.button("⬅ Back to List"):
            st.session_state["view"] = "list"
            st.rerun()
        ticker_search_view()

    elif current_view == "edit":
        render_edit_view()

    else:
        render_list_view()

def render_list_view():
    st.title("Asset Static Data")
    
    if st.button("➕ New ISIN"):
        st.session_state["view"] = "search"
        st.rerun()

    data = get_all_assets_with_labels()
    if not data:
        st.info("No records found.")
        return

    df = pd.DataFrame(data)


    # --- ADVANCED DYNAMIC FILTER SECTION ---
    with st.expander("🛠 Advanced Query Builder", expanded=False):
        logic_mode = st.radio("Combination Logic", ["Match ALL (AND)", "Match ANY (OR)"], horizontal=True)
        if "filter_rules" not in st.session_state: 
            st.session_state["filter_rules"] = []
        
        c1, c2 = st.columns([1, 4])
        if c1.button("➕ Add Rule"): 
            st.session_state["filter_rules"].append({"column": df.columns[0], "value": None})
        if c2.button("🗑 Clear All"):
            st.session_state["filter_rules"] = []
            st.rerun()

        active_filters = []
        for i, rule in enumerate(st.session_state["filter_rules"]):
            r_col1, r_col2, r_col3 = st.columns([2, 3, 0.5])
            
            col_name = r_col1.selectbox(f"Column {i}", df.columns, key=f"fcol_{i}")
            
            # --- CUSTOM LOGIC FOR CLOSED ON ---
            if col_name == "Closed On":
                val = r_col2.selectbox(
                    f"Criteria {i}", 
                    ["Is Null (Active Assets)", "Is Not Null (Closed Assets)"], 
                    key=f"fval_{i}"
                )
                
                if val == "Is Null (Active Assets)":
                    active_filters.append(df[col_name].isna())
                else:
                    active_filters.append(df[col_name].notna())
            
            # --- STANDARD LOGIC FOR ALL OTHER COLUMNS ---
            else:
                options = sorted(df[col_name].dropna().unique().astype(str).tolist())
                val = r_col2.multiselect(f"Values {i}", options, key=f"fval_{i}")
                if val: 
                    active_filters.append(df[col_name].astype(str).isin(val))

            if r_col3.button("❌", key=f"frem_{i}"):
                st.session_state["filter_rules"].pop(i)
                st.rerun()

    # --- APPLY FILTER LOGIC ---
    filtered_df = df.copy()
    if active_filters:
        mask = active_filters[0]
        for m in active_filters[1:]:
            mask = (mask & m) if logic_mode == "Match ALL (AND)" else (mask | m)
        filtered_df = df[mask]


    st.info(f"Displaying {len(filtered_df)} assets.")

    # --- TABLE WITH EDIT LINK ---
    # We use a trick: add a column to trigger edit mode
    # In Streamlit, the easiest way to "click a row" is using the selection state of the dataframe
    event = st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )

    if event.selection.rows:
        selected_index = event.selection.rows[0]
        st.session_state["edit_isin"] = filtered_df.iloc[selected_index]["ISIN"]
        st.session_state["view"] = "edit"
        st.rerun()

def render_edit_view():
    isin = st.session_state.get("edit_isin")
    st.subheader(f"Edit Asset: {isin}")
    
    if st.button("⬅ Cancel"):
        st.session_state["view"] = "list"
        st.rerun()

    # Load current data
    all_data = get_all_assets_with_labels()
    asset = next((item for item in all_data if item["ISIN"] == isin), None)

    if not asset:
        st.error("Asset not found.")
        return

    # --- CLOSE / REOPEN LOGIC ---
    st.write("---")
    closed_val = asset.get("Closed On") # Based on the dict key in database.py
    
    if closed_val is None:
        if st.button("🔒 Close Asset", help="Set the closing date to today", use_container_width=True):
            update_asset_static_data(isin, {
                "closed_on": datetime.now().date().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "updated_by": st.session_state.get("user_name", "System")
            })
            st.success("Asset closed.")
            st.cache_data.clear()
            st.session_state["view"] = "list"
            st.rerun()
    else:
        st.warning(f"This asset was closed on {closed_val}")
        if st.button("🔓 Reopen Asset", help="Clear the closing date", use_container_width=True):
            update_asset_static_data(isin, {
                "closed_on": None,
                "updated_at": datetime.now().isoformat(),
                "updated_by": st.session_state.get("user_name", "System")
            })
            st.success("Asset reopened.")
            st.cache_data.clear()
            st.session_state["view"] = "list"
            st.rerun()
    st.write("---")

    # --- MAIN EDIT FORM ---
    # Load Ref Options if not in session
    # Robust check: If 'opt_source' is missing, reload reference data
    if 'opt_source' not in st.session_state:
        with st.spinner("Loading reference data..."):
            st.session_state['opt_asset'] = get_ref_options("ref_asset_class")
            st.session_state['opt_gics'] = get_ref_options("ref_sector")
            st.session_state['opt_region'] = get_ref_options("ref_region")
            st.session_state['opt_type'] = get_ref_options("ref_instrument_type")
            st.session_state['opt_source'] = get_ref_options("ref_price_source")
            st.session_state['ref_data_loaded'] = True

    with st.form("edit_form"):
        col1, col2 = st.columns(2)
        col1.text_input("ISIN (Primary Key)", value=isin, disabled=True)
        name = col1.text_input("Name", value=asset["Name"])
        ticker = col2.text_input("Ticker", value=asset["Ticker"])
        currency = col2.text_input("Currency", value=asset["Currency"])
        
        def get_index(options, current_label):
            try: return next(i for i, s in enumerate(options) if f"({current_label})" in s)
            except: return 0

        asset_class = col1.selectbox("Asset Class", st.session_state['opt_asset'], index=get_index(st.session_state['opt_asset'], asset["Asset Class"]))
        region = col2.selectbox("Region", st.session_state['opt_region'], index=get_index(st.session_state['opt_region'], asset["Region"]))
        sector = col1.selectbox("Sector", st.session_state['opt_gics'], index=get_index(st.session_state['opt_gics'], asset["Sector"]))
        instr_type = col2.selectbox("Instrument Type", st.session_state['opt_type'], index=get_index(st.session_state['opt_type'], asset["Type"]))
        source = col1.selectbox("Price Source", st.session_state['opt_source'], index=get_index(st.session_state['opt_source'], asset["Price Source"]))
        
        industry = col2.text_input("Industry", value=asset["Industry"])
        country = col1.text_input("Country", value=asset["Country"])

        if st.form_submit_button("Save Changes", type="primary"):
            updated_payload = {
                "name": name,
                "ticker": ticker,
                "currency": currency,
                "asset_class_code": asset_class.split(" (")[0],
                "region_code": region.split(" (")[0],
                "sector_code": sector.split(" (")[0],
                "instrument_type": instr_type.split(" (")[0],
                "price_source": source.split(" (")[0],
                "industry": industry,
                "country": country,
                "updated_at": datetime.now().isoformat(),
                "updated_by": st.session_state.get("user_name", "System")
            }
            update_asset_static_data(isin, updated_payload)
            st.success("Asset updated successfully!")
            st.cache_data.clear()
            st.session_state["view"] = "list"
            st.rerun()





