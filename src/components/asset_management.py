import streamlit as st
import pandas as pd
from datetime import datetime
from src.database import (
    get_all_assets_with_labels, 
    update_asset_static_data, 
    get_ref_options,
    save_asset_static_data,
    search_exchange_tickers
)
from src.utils import (
    extract_code, 
    get_option_index, 
    get_option_index_by_label,
    get_selectbox_options_and_index,
    ensure_reference_data, 
    apply_advanced_filters,
    yfinance_search_component,
    my_yf,
    my_tiingo
)

def asset_form_component(mode="new", asset=None, version=0):
    """
    Zentrale, wiederverwendbare UI-Komponente für das Asset-Formular.
    
    :param mode: "new" für Neuanlage, "edit" für Bearbeitung
    :param asset: Das originale Asset-Dict aus der Datenbank (nur bei "edit")
    :param version: Die aktuelle form_version / new_asset_form_version für den Reset-Key
    """
    ensure_reference_data()
    
    # Präfixe für Keys und Formular-ID bestimmen
    form_id = "new_asset_form" if mode == "new" else "edit_form"
    key_prefix = "new_f" if mode == "new" else "f"
    gap = "&nbsp;" * 6
    
    # Hilfsfunktion für Labels (zeigt Originalwert nur im Edit-Modus)
    def get_label(label_text, field_key):
        if mode == "edit" and asset and field_key in asset:
            return f"{label_text}{gap}:blue[(original: {asset[field_key]})]"
        return f"{label_text}{gap}"

    # Hilfsfunktion für Default-Werte
    def get_default_value(prefill_key, asset_key):
        if mode == "edit" and asset:
            return st.session_state.get(f"prefill_{prefill_key}", asset.get(asset_key, ""))
        return st.session_state.get(f"prefill_{prefill_key}", "")

    with st.form(form_id):
        col1, col2 = st.columns(2)
        
        # ISIN Steuerung (Bei "new" editierbar, bei "edit" gesperrt)
        if mode == "new":
            isin = col1.text_input("ISIN (Primary Key)", value=st.session_state.get("prefill_isin", ""), key=f"{key_prefix}n_isin_{version}")
        else:
            isin = st.session_state.get("edit_isin")
            col1.text_input("ISIN (Primary Key)", value=isin, disabled=True)

        # Textfelder
        name = col1.text_input(get_label("Name", "Name"), value=get_default_value("name", "Name"), key=f"{key_prefix}n_{version}")       
        ticker = col2.text_input(get_label("Ticker", "Ticker"), value=get_default_value("ticker", "Ticker"), key=f"{key_prefix}t_{version}")
        risk_currency = col2.text_input(get_label("Risk Currency", "Risk Currency"), value=get_default_value("risk_currency", "Risk Currency"), key=f"{key_prefix}rc_{version}")
        price_currency = col2.text_input(get_label("Price Currency", "Price Currency"), value=get_default_value("price_currency", "Price Currency"), key=f"{key_prefix}pc_{version}") 

        # Selectboxen mit Index-Ermittlung
        asset_class_opt, asset_class_idx = get_selectbox_options_and_index(
            st.session_state['opt_asset'], get_default_value("asset_class", "Asset Class")
        )
        asset_class = col1.selectbox(get_label("Asset Class", "Asset Class"), asset_class_opt, index=asset_class_idx, key=f"{key_prefix}ac_{version}")
        
        region_opt, region_idx = get_selectbox_options_and_index(
            st.session_state['opt_region'], get_default_value("region", "Region")
        )
        region = col2.selectbox(get_label("Region", "Region"), region_opt, index=region_idx, key=f"{key_prefix}r_{version}")
        
        sector_opt, sector_idx = get_selectbox_options_and_index(
            st.session_state['opt_gics'], get_default_value("sector", "Sector")
        )
        sector = col1.selectbox(get_label("Sector", "Sector"), sector_opt, index=sector_idx, key=f"{key_prefix}s_{version}")
        
        instr_type_opt, instr_type_idx = get_selectbox_options_and_index(
            st.session_state['opt_type'], get_default_value("instrument_type", "Type")
        )
        instr_type = col2.selectbox(get_label("Instrument Type", "Type"), instr_type_opt, index=instr_type_idx, key=f"{key_prefix}it_{version}")
        
        source_opt, source_idx = get_selectbox_options_and_index(
            st.session_state['opt_source'], get_default_value("price_source", "Price Source")
        )
        source = col1.selectbox(get_label("Price Source", "Price Source"), source_opt, index=source_idx, key=f"{key_prefix}ps_{version}")
        
        # Restliche Textfelder
        industry = col2.text_input(get_label("Industry", "Industry"), value=get_default_value("industry", "Industry"), key=f"{key_prefix}i_{version}")
        country = col1.text_input(get_label("Country", "Country"), value=get_default_value("country", "Country"), key=f"{key_prefix}cty_{version}")

        # --- NEU: BUTTON-ZEILE (Nebeneinander platziert) ---
        st.markdown(" ") # Kleiner Abstandhalter
        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
        
        with btn_col1:
            submit_btn_label = "Save to Database" if mode == "new" else "Save Changes"
            submit_clicked = st.form_submit_button(submit_btn_label, type="primary")
            
        with btn_col2:
            check_price_clicked = st.form_submit_button("🔍 Check Current Price", type="secondary")

        with btn_col3:
            search_ticker_clicked = st.form_submit_button("🔎 Search Ticker", type="secondary")

        # --- LOGIK: PREIS PRÜFEN (Abfangen vor der Speicherlogik) ---
        if check_price_clicked:
            if not ticker:
                st.error("Please enter a Ticker first to check prices.")
            else:
                source_code = extract_code(source) if source != "(None)" else ""
                
                with st.spinner(f"Fetching price for '{ticker}' via {source_code}..."):
                    price = None
                    curr = None
                    
                    if source_code == "YFN":
                        try:
                            # Ticker-Objekt über den geladenen Proxy abfragen
                            ticker_obj = my_yf.Ticker(ticker)
                            # Im echten yfinance liegt der Kurs oft in .info; im Mock ebenfalls vorhanden
                            price = ticker_obj.info.get("currentPrice") or ticker_obj.info.get("regularMarketPrice")
                            curr = ticker_obj.info.get("currency")
                            
                            # Fallback falls history herhalten muss (falls .info leer ist)
                            if price is None:
                                hist = ticker_obj.history(period="1d")
                                if not hist.empty:
                                    price = hist["Close"].iloc[-1]
                        except Exception as e:
                            st.error(f"Error fetching from Yahoo Finance: {e}")
                            
                    elif source_code == "TGO":
                        try:
                            # Abfrage über den neuen Tiingo Wrapper
                            res = my_tiingo.get_latest_price(ticker)
                            price = res.get("price")
                            curr = res.get("currency")
                        except Exception as e:
                            st.error(f"Error fetching from Tiingo: {e}")
                    else:
                        st.warning(f"No pricing integration available for Price Source code: '{source_code}'. Please use YFN or TGO.")
                    
                    # Ergebnis visualisieren
                    if price is not None:
                        st.info(f"**Latest Price:** {price:,.4f} {curr if curr else ''}")
                    elif source_code in ["YFN", "TGO"]:
                        st.error(f"Could not extract a valid price for Ticker '{ticker}'. Check if symbol is correct.")

        # --- LOGIK: SUCHE NACH TICKERDATEN ---
        if search_ticker_clicked:
            if not isin and not name:
                st.error("Please enter either ISIN or Name to search tickers.")
            else:
                with st.spinner("Searching for matching tickers..."):
                    try:
                        results = search_exchange_tickers(isin=isin, name=name)
                    except Exception as e:
                        st.error(f"Error searching ticker master data: {e}")
                        results = []

                st.session_state[f"{form_id}_ticker_search_results"] = results
                st.session_state[f"{form_id}_ticker_search_terms"] = {
                    "isin": isin,
                    "name": name,
                }

        # --- LOGIK BEIM SPEICHERN ---
        if submit_clicked:
            if mode == "new" and (not isin or len(isin) < 5):
                st.error("Please enter a valid ISIN before saving.")
                return

            def extract_code_or_none(selected_value):
                return None if selected_value == "(None)" else extract_code(selected_value)

            # Gemeinsames Payload-Mapping
            payload = {
                "name": name,
                "ticker": ticker,
                "risk_currency": risk_currency,
                "price_currency": price_currency,
                "asset_class_code": extract_code_or_none(asset_class),
                "region_code": extract_code_or_none(region),
                "sector_code": extract_code_or_none(sector),
                "instrument_type_code": extract_code_or_none(instr_type),
                "price_source_code": extract_code_or_none(source),
                "industry": industry,
                "country": country,
            }

            try:
                if mode == "new":
                    payload.update({
                        "isin": isin,
                        "price_start_date": datetime.now().date().isoformat(),
                        "created_by": st.session_state.get('user_id'),
                        "updated_by": None
                    })
                    save_asset_static_data(payload)
                    st.success(f"✅ {ticker} saved successfully!")
                else:
                    payload.update({
                        "updated_at": datetime.now().isoformat(),
                        "updated_by": st.session_state.get("user_id")
                    })
                    update_asset_static_data(isin, payload)
                    st.success("Asset updated successfully!")
                
                st.cache_data.clear()
                
                # Session State aufräumen
                keys_to_clear = [
                    "prefill_name", "prefill_ticker", "prefill_risk_currency", "prefill_price_currency", 
                    "prefill_asset_class", "prefill_region", "prefill_sector", "prefill_instrument_type", 
                    "prefill_industry", "prefill_country", "prefill_price_source", "prefill_isin",
                    "new_asset_form_version", "form_version", "last_edit_isin", "last_search_input"
                ]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]

                st.session_state["view"] = "list"
                st.rerun()
            except Exception as e:
                st.error(f"Error saving data: {e}")

    # Search results outside the form ensure the table remains visible after submit/rerun.
    results_key = f"{form_id}_ticker_search_results"
    if results_key in st.session_state:
        results = st.session_state.get(results_key, []) or []
        if results:
            df_results = pd.DataFrame(results)
            
            # Extract exchange name from nested ref_exchange object
            df_results["exchange_name"] = df_results["ref_exchange"].apply(
                lambda x: x["name"] if isinstance(x, dict) and "name" in x else "Unknown"
            )
            
            df_results = df_results.rename(columns={
                "ticker_code": "Ticker",
                "exchange_code": "Exchange",
                "exchange_name": "Exchange Name",
                "price_source_code": "Source",
                "name": "Name",
                "country": "Country",
                "currency": "Currency",
                "type": "Type",
                "isin": "ISIN"
            })[["Ticker", "Exchange", "Exchange Name", "Source", "Name", "Country", "Currency", "Type", "ISIN"]]
            st.subheader("Ticker Search Results")
            st.dataframe(df_results, use_container_width=True)
        else:
            st.warning("No matching tickers found for the entered ISIN/Name.")

        # Keep the search terms visible for context
        terms = st.session_state.get(f"{form_id}_ticker_search_terms", {})
        if terms:
            st.caption(f"Search terms: ISIN={terms.get('isin','')} Name={terms.get('name','')}")





def ticker_search_view():
    st.subheader("🔍 Search New Asset")
    ensure_reference_data()

    # --- NEU: Version Tracker für Formular-Reset ---
    if "new_asset_form_version" not in st.session_state:
        st.session_state["new_asset_form_version"] = 0
    v = st.session_state["new_asset_form_version"]

    # Only reset previous yfinance results when a new search session starts
    if st.session_state.get("last_search_input") != st.session_state.get("current_search_input"):
        reload_keys = ["ticker_search_results_df", "ticker_search_editor", "ticker_search_ticker_select"]
        for key in reload_keys:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state["current_search_input"] = st.session_state.get("last_search_input")
        st.session_state["new_asset_form_version"] = 0
        v = 0

    search_input = st.text_input("Enter ISIN, Ticker or Name", placeholder="e.g. AU000000DRO2 or Apple")
    st.session_state["last_search_input"] = search_input
    
    selected_row, edited_df = yfinance_search_component(search_input, session_key_prefix="ticker_search")

    if selected_row is not None and edited_df is not None:
        if st.button("Prefill Asset with loaded Data", type="primary"):
            if not selected_row["ISIN"] or len(selected_row["ISIN"]) < 5:
                st.error("Please enter a valid ISIN in the table above before prefilling.")
            else:
                # Pre-fill the form fields with the selected data (same as "Update Asset with Reloaded Data")
                st.session_state["prefill_name"] = selected_row["Name"]
                st.session_state["prefill_ticker"] = selected_row["Ticker"]
                st.session_state["prefill_risk_currency"] = selected_row.get("Risk Currency") or selected_row.get("Currency")
                st.session_state["prefill_price_currency"] = selected_row.get("Price Currency") or selected_row.get("Currency")
                st.session_state["prefill_asset_class"] = selected_row["AssetClass"]
                st.session_state["prefill_region"] = selected_row["Region"]
                st.session_state["prefill_sector"] = selected_row["Sector_GICS"]
                st.session_state["prefill_instrument_type"] = selected_row["InstrumentType"]
                st.session_state["prefill_industry"] = selected_row["Industry"]
                st.session_state["prefill_country"] = selected_row["Country"]
                st.session_state["prefill_isin"] = selected_row["ISIN"]
                # Pre-fill Price Source with YFN
                price_source_option = next((s for s in st.session_state['opt_source'] if s.startswith("YFN")), None)
                if price_source_option:
                    st.session_state["prefill_price_source"] = price_source_option
                
                # Increment version to force widget updates
                st.session_state["new_asset_form_version"] += 1
                
                st.success("Form pre-filled with loaded data. Please review and save below.")
                st.rerun()
    
    # --- MAIN EDIT FORM FOR NEW ASSET ---
    # Only show the form if prefill data is available
    if "prefill_isin" in st.session_state:
        st.markdown("---")
        st.subheader("📝 Review & Edit New Asset Data")

        asset_form_component(mode="new", version=v)     



def asset_table_view():
    # --- VIEW ROUTING ---
    current_view = st.session_state.get("view", "list")

    if current_view == "search":
        if st.button("⬅ Back to List"):
            keys_to_clear = [
                "prefill_name", "prefill_ticker", "prefill_risk_currency", "prefill_price_currency", 
                "prefill_asset_class", "prefill_region", "prefill_sector", "prefill_instrument_type", 
                "prefill_industry", "prefill_country", "prefill_price_source", "prefill_isin",
                "new_asset_form_version", "last_search_input", "current_search_input"
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
                    
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
        "ISIN", "Name", "Ticker", "Risk Currency", "Type", 
        "Asset Class", "Region", "Sector", "Industry", 
        "Country", "Price Source", "Price Currency", "Price Start Date", "Closed On", 
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
    
    # --- NEU: Version Tracker für Formular-Reset ---
    if "form_version" not in st.session_state:
        st.session_state["form_version"] = 0
    v = st.session_state["form_version"]

    # Only reset previous yfinance results when a new asset edit session starts
    if st.session_state.get("last_edit_isin") != isin:
        reload_keys = ["reload_results_df", "reload_editor", "reload_ticker_select"]
        for key in reload_keys:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state["last_edit_isin"] = isin
        # Bei neuem Asset Version zurücksetzen
        st.session_state["form_version"] = 0
        v = 0

    # 1. Spalten für die obere Button-Leiste definieren
    # [1, 1, 4] bedeutet: zwei kleine Spalten für Buttons, eine große leere Spalte rechts
    col_back, col_status, col_spacer = st.columns([1, 1.2, 4])

    with col_back:
        if st.button("⬅ Cancel"):
            keys_to_clear = [
                "prefill_name", "prefill_ticker", "prefill_risk_currency", "prefill_price_currency", 
                "prefill_asset_class", "prefill_region", "prefill_sector", "prefill_instrument_type", 
                "prefill_industry", "prefill_country", "prefill_price_source", "form_version", 
                "last_edit_isin"
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
                    
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
                    "updated_by": st.session_state.get("user_id")
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
                    "updated_by": st.session_state.get("user_id")
                })
                st.success("Asset reopened.")
                st.cache_data.clear()
                st.session_state["view"] = "list"
                st.rerun()

    # Den Warntext (falls geschlossen) kannst du darunter platzieren
    if closed_val:
        st.warning(f"This asset was closed on {closed_val}")

    selected_row, edited_df = yfinance_search_component(search_input=isin, session_key_prefix="reload")
    
    if selected_row is not None and edited_df is not None:
        if st.button("Update Asset with Reloaded Data", type="primary"):
            # Pre-fill the form fields with the selected data
            st.session_state["prefill_name"] = selected_row["Name"]
            st.session_state["prefill_ticker"] = selected_row["Ticker"]
            st.session_state["prefill_risk_currency"] = selected_row.get("Risk Currency") or selected_row.get("Currency")
            st.session_state["prefill_price_currency"] = selected_row.get("Price Currency") or selected_row.get("Currency")
            st.session_state["prefill_asset_class"] = selected_row["AssetClass"]
            st.session_state["prefill_region"] = selected_row["Region"]
            st.session_state["prefill_sector"] = selected_row["Sector_GICS"]
            st.session_state["prefill_instrument_type"] = selected_row["InstrumentType"]
            st.session_state["prefill_industry"] = selected_row["Industry"]
            st.session_state["prefill_country"] = selected_row["Country"]
            # Pre-fill Price Source with YFN
            price_source_option = next((s for s in st.session_state['opt_source'] if s.startswith("YFN")), None)
            if price_source_option:
                st.session_state["prefill_price_source"] = price_source_option
            
            # --- NEU: Version erhöhen, um Keys zu ändern und Widgets zum Update zu zwingen ---
            st.session_state["form_version"] += 1
            
            st.success("Form pre-filled with reloaded data. Please review and save below.")
            st.rerun()

    asset_form_component(mode="edit", asset=asset, version=v)

