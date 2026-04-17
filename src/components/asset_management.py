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



def render_list_view():
    st.title("Asset Static Data")
    
    # 1. Navigation
    if st.button("➕ New ISIN"):
        st.session_state["view"] = "search"
        st.rerun()

    # 2. Data Loading & Filtering
    data = get_all_assets_with_labels()
    if not data:
        st.info("No records found.")
        return

    df = pd.DataFrame(data)

    # Filtering logic (remains the same)
    def closed_on_logic(df_in, widget_col, index, prefix):
        selection = widget_col.selectbox(
            f"Criteria {index}", 
            ["Is Null (Active Assets)", "Is Not Null (Closed Assets)"], 
            key=f"{prefix}_closed_val_{index}"
        )
        return df_in["Closed On"].isna() if selection == "Is Null (Active Assets)" else df_in["Closed On"].notna()

    filtered_df = apply_advanced_filters(df, session_prefix="asset_management", custom_filter_logic={"Closed On": closed_on_logic})

    # 3. Column Order (as requested)
    column_order = [
        "ISIN", "Name", "Ticker", "Currency", "Type", 
        "Asset Class", "Region", "Sector", "Industry", 
        "Country", "Price Source", "Closed On", 
        "Created At", "Created By", "Updated At", "Updated By"
    ]
    existing_cols = [c for c in column_order if c in filtered_df.columns]
    display_df = filtered_df[existing_cols]

    # --- VISUAL FEEDBACK ---
    st.info(f"Displaying {len(display_df)} assets. **Select a row using the button on the left to edit.**")

    # 4. DATA TABLE (Native Selection - No Page Reload)
    # This is the ONLY way to stay in the same session without losing login.
    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",           # Trigger rerun within the SAME session
        selection_mode="single-row", # Enables the radio-button on the left
    )

    # 5. SELECTION LOGIC
    # This triggers instantly without opening new tabs or losing login status
    if event.selection.rows:
        selected_index = event.selection.rows[0]
        st.session_state["edit_isin"] = display_df.iloc[selected_index]["ISIN"]
        st.session_state["view"] = "edit"
        st.rerun()


def render_edit_view():
    isin = st.session_state.get("edit_isin")
    st.subheader(f"Edit Asset: {isin}")
    
    if st.button("⬅ Cancel"):
        st.session_state["view"] = "list"
        st.rerun()

    # 1. Load current data
    all_data = get_all_assets_with_labels()
    asset = next((item for item in all_data if item["ISIN"] == isin), None)

    if not asset:
        st.error("Asset not found.")
        return

    # --- CLOSE / REOPEN LOGIC ---
    st.write("---")
    closed_val = asset.get("Closed On")
    
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
    # REPLACEMENT 1: Using our central loader instead of the long IF-block
    ensure_reference_data()

    with st.form("edit_form"):
        col1, col2 = st.columns(2)
        col1.text_input("ISIN (Primary Key)", value=isin, disabled=True)
        name = col1.text_input("Name", value=asset["Name"])
        ticker = col2.text_input("Ticker", value=asset["Ticker"])
        currency = col2.text_input("Currency", value=asset["Currency"])
        
        # Hinweis: Die Keys hier (z.B. asset["Asset Class"]) müssen 
        # exakt so heißen wie im flattened_data dict der database.py!
        asset_class = col1.selectbox("Asset Class", st.session_state['opt_asset'], 
                                     index=get_option_index(st.session_state['opt_asset'], asset["Asset Class"]))
        
        region = col2.selectbox("Region", st.session_state['opt_region'], 
                                index=get_option_index(st.session_state['opt_region'], asset["Region"]))
        
        sector = col1.selectbox("Sector", st.session_state['opt_gics'], 
                                index=get_option_index(st.session_state['opt_gics'], asset["Sector"]))
        
        instr_type = col2.selectbox("Instrument Type", st.session_state['opt_type'], 
                                    index=get_option_index(st.session_state['opt_type'], asset["Type"]))
        
        source = col1.selectbox("Price Source", st.session_state['opt_source'], 
                                index=get_option_index(st.session_state['opt_source'], asset["Price Source"]))
        
        industry = col2.text_input("Industry", value=asset["Industry"])
        country = col1.text_input("Country", value=asset["Country"])

        if st.form_submit_button("Save Changes", type="primary"):
            updated_payload = {
                "name": name,
                "ticker": ticker,
                "currency": currency,
                "asset_class_code": extract_code(asset_class),
                "region_code": extract_code(region),
                "sector_code": extract_code(sector),
                "instrument_type_code": extract_code(instr_type), # Korrigiert: _code
                "price_source_code": extract_code(source),       # Korrigiert: _code
                "industry": industry,
                "country": country,
                "updated_at": datetime.now().isoformat(),
                "updated_by": st.session_state.get("user_name", "System")
            }
            update_asset_static_data(isin, updated_payload)
            st.success("Asset updated successfully!")
            # WICHTIG: Cache leeren, damit die Liste die neuen Daten zeigt
            st.cache_data.clear() 
            st.session_state["view"] = "list"
            st.rerun()




