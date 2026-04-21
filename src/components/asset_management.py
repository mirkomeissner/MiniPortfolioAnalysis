import streamlit as st
import pandas as pd
import yfinance as yf
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
from src.utils.ui_components import yfinance_search_component
from .ticker_search import ticker_search_view

# --- HELPER FUNCTIONS FROM ticker_search.py ---

# Helper functions moved to ui_components.py

# handle_reload_save function removed - now pre-filling form instead of direct save

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
    
    # 1. Spalten für die obere Button-Leiste definieren
    # [1, 1, 4] bedeutet: zwei kleine Spalten für Buttons, eine große leere Spalte rechts
    col_back, col_status, col_spacer = st.columns([1, 1.2, 4])

    with col_back:
        if st.button("⬅ Cancel"):
            st.session_state["view"] = "list"
            st.rerun()

    # 2. Daten laden (wie gehabt)
    all_data = get_all_assets_with_labels()
    asset = next((item for item in all_data if item["ISIN"] == isin), None)

    if not asset:
        st.error("Asset not found.")
        return

    closed_val = asset.get("Closed On")

    # 3. Status-Button in die zweite Spalte platzieren
    with col_status:
        if closed_val is None:
            if st.button("🔒 Close Asset", help="Set the closing date to today"):
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
            if st.button("🔓 Reopen Asset", help="Clear the closing date"):
                update_asset_static_data(isin, {
                    "closed_on": None,
                    "updated_at": datetime.now().isoformat(),
                    "updated_by": st.session_state.get("user_name", "System")
                })
                st.success("Asset reopened.")
                st.cache_data.clear()
                st.session_state["view"] = "list"
                st.rerun()

    # Den Warntext (falls geschlossen) kannst du darunter platzieren
    if closed_val:
        st.warning(f"This asset was closed on {closed_val}")

    st.write("---")

    # --- RELOAD FROM YAHOO FINANCE ---
    # search_input = st.text_input("Enter ISIN, Ticker or Name for reload", placeholder="e.g. AU000000DRO2 or Apple", key="reload_search_input")
    
    selected_row, edited_df = yfinance_search_component(search_input = isin, session_key_prefix="reload", allow_isin_edit=False)
    
    if selected_row is not None and edited_df is not None:
        if st.button("Update Asset with Reloaded Data", type="primary"):
            # Pre-fill the form fields with the selected data
            st.session_state["prefill_name"] = selected_row["Name"]
            st.session_state["prefill_ticker"] = selected_row["Ticker"]
            st.session_state["prefill_currency"] = selected_row["Currency"]
            st.session_state["prefill_asset_class"] = selected_row["AssetClass"]
            st.session_state["prefill_region"] = selected_row["Region"]
            st.session_state["prefill_sector"] = selected_row["Sector_GICS"]
            st.session_state["prefill_instrument_type"] = selected_row["InstrumentType"]
            st.session_state["prefill_industry"] = selected_row["Industry"]
            st.session_state["prefill_country"] = selected_row["Country"]
            st.success("Form pre-filled with reloaded data. Please review and save below.")
            st.rerun()

    st.write("---")

    # --- MAIN EDIT FORM ---
    # REPLACEMENT 1: Using our central loader instead of the long IF-block
    ensure_reference_data()

    with st.form("edit_form"):
        col1, col2 = st.columns(2)
        col1.text_input("ISIN (Primary Key)", value=isin, disabled=True)
        name = col1.text_input("Name", value=st.session_state.get("prefill_name", asset["Name"]))
        ticker = col2.text_input("Ticker", value=st.session_state.get("prefill_ticker", asset["Ticker"]))
        currency = col2.text_input("Currency", value=st.session_state.get("prefill_currency", asset["Currency"]))
        
        # Hinweis: Die Keys hier (z.B. asset["Asset Class"]) müssen 
        # exakt so heißen wie im flattened_data dict der database.py!
        asset_class = col1.selectbox("Asset Class", st.session_state['opt_asset'], 
                                     index=get_option_index(st.session_state['opt_asset'], st.session_state.get("prefill_asset_class", asset["Asset Class"])))
        
        region = col2.selectbox("Region", st.session_state['opt_region'], 
                                index=get_option_index(st.session_state['opt_region'], st.session_state.get("prefill_region", asset["Region"])))
        
        sector = col1.selectbox("Sector", st.session_state['opt_gics'], 
                                index=get_option_index(st.session_state['opt_gics'], st.session_state.get("prefill_sector", asset["Sector"])))
        
        instr_type = col2.selectbox("Instrument Type", st.session_state['opt_type'], 
                                    index=get_option_index(st.session_state['opt_type'], st.session_state.get("prefill_instrument_type", asset["Type"])))
        
        source = col1.selectbox("Price Source", st.session_state['opt_source'], 
                                index=get_option_index(st.session_state['opt_source'], asset["Price Source"]))
        
        industry = col2.text_input("Industry", value=st.session_state.get("prefill_industry", asset["Industry"]))
        country = col1.text_input("Country", value=st.session_state.get("prefill_country", asset["Country"]))

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
            # Clear prefill data
            for key in ["prefill_name", "prefill_ticker", "prefill_currency", "prefill_asset_class", 
                       "prefill_region", "prefill_sector", "prefill_instrument_type", "prefill_industry", "prefill_country"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state["view"] = "list"
            st.rerun()




