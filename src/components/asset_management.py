import streamlit as st
import pandas as pd
from datetime import datetime
from src.database import (
    get_all_assets_with_labels, 
    update_asset_static_data, 
    get_ref_options
)
from src.utils import (
    extract_code, 
    get_option_index, 
    ensure_reference_data, 
    apply_advanced_filters
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



import streamlit as st
import pandas as pd
from src.database import get_all_assets_with_labels
from src.utils import apply_advanced_filters

def render_list_view():
    """
    Renders the main table view of all assets with advanced filtering capabilities.
    """
    st.header("Asset Inventory")

    # 1. Fetch data from database
    data = get_all_assets_with_labels()
    if not data:
        st.info("No assets found in the database.")
        return

    df = pd.DataFrame(data)

    # 2. Define custom filter logic for special columns (e.g., 'Closed On')
    # This allows us to filter by 'Active' vs 'Closed' status easily
    def closed_status_filter(df_in, container, index, prefix):
        choice = container.selectbox(
            f"Asset Status {index}", 
            ["Active Assets (Open)", "Closed Assets"], 
            key=f"{prefix}_status_choice_{index}"
        )
        if "Active" in choice:
            return df_in["Closed On"].isna()
        else:
            return df_in["Closed On"].notna()

    # 3. Apply centralized filters
    # session_prefix ensures that filter states don't clash with other screens
    filtered_df = apply_advanced_filters(
        df, 
        session_prefix="asset_inventory",
        custom_filter_logic={"Closed On": closed_status_filter}
    )

    # 4. Display Results
    st.write(f"Showing {len(filtered_df)} of {len(df)} assets.")
    st.dataframe(
        filtered_df, 
        use_container_width=True, 
        hide_index=True
    )

    if st.button("➕ Add New Asset"):
        st.session_state["view"] = "add"
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
            if not current_label: return 0
            try: 
                # Sucht nach dem Label im String, z.B. "STO (Stock)"
                return next(i for i, s in enumerate(options) if f"({current_label})" in s or s.startswith(current_label))
            except: 
                return 0

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





