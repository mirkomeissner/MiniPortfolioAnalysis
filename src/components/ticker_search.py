def ticker_search_view():
    st.title("🔍 Ticker Search & Edit")
    st.write("Search via ISIN and refine the metadata before saving.")

    # 1. Load REF-data into session state
    if 'ref_data_loaded' not in st.session_state:
        with st.spinner("Initializing reference data..."):
            st.session_state['db_region_map'] = get_country_mapping()
            st.session_state['ref_sectors'] = get_ref_options("ref_sector")
            st.session_state['ref_regions'] = get_ref_options("ref_region")
            st.session_state['ref_instr_types'] = get_ref_options("ref_instrument_type")
            st.session_state['ref_asset_classes'] = get_ref_options("ref_asset_class") # Check: Tabelle heißt ref_asset_class
            st.session_state['ref_data_loaded'] = True

    # Input Area
    col1, col2 = st.columns([3, 1])
    with col1:
        isin_input = st.text_input("Enter ISIN", placeholder="e.g. US0378331005", key="isin_field")
    with col2:
        st.write("##")
        search_button = st.button("Search Ticker", use_container_width=True)

    if search_button and isin_input:
        with st.spinner(f"Searching for {isin_input}..."):
            try:
                search_results = yf.Search(isin_input).quotes
                if not search_results:
                    st.warning("No tickers found for this ISIN.")
                else:
                    raw_data = []
                    for res in search_results:
                        symbol = res.get("symbol")
                        ticker_obj = yf.Ticker(symbol)
                        info = ticker_obj.info
                        name = info.get("longName") or res.get("longname") or "Unknown Name"
                        country = info.get("country", "Unknown")
                        currency = info.get("currency", "???")
                        
                        # Mappings
                        if any(word in name.upper() for word in ["WORLD", "GLOBAL", "ALL COUNTRY"]):
                            mapped_region = "GLO"
                        elif "DEVELOPED" in name.upper():
                            mapped_region = "DEV"
                        else:
                            mapped_region = st.session_state['db_region_map'].get(country, "GLO")

                        yahoo_sector = info.get("sector")
                        gics_code = map_yahoo_to_ref(yahoo_sector)
                        raw_type = res.get("quoteType") or info.get("quoteType") or "EQUITY"
                        instr_type = map_yahoo_to_instrument_type(raw_type, name)
                        
                        # ASSET CLASS MAPPING
                        a_class = map_yahoo_to_asset_class(raw_type, name)

                        # Volume
                        hist = ticker_obj.history(period="7d")
                        avg_volume = hist['Volume'].mean() if not hist.empty else 0
                        
                        # Dictionary erstellen
                        row = {
                            "Ticker": symbol,
                            "Name": name,
                            "Exchange": info.get("exchange"),
                            "Currency": currency,
                            "AssetClass": a_class, # Muss hier drin sein
                            "Industry": info.get("industry"),
                            "Sector": yahoo_sector,
                            "Sector_GICS": gics_code,
                            "Country": country,
                            "Region": mapped_region,
                            "InstrumentType_Raw": raw_type,
                            "InstrumentType": instr_type,
                            "Vol (7d Avg)": int(avg_volume)
                        }
                        raw_data.append(row)
                    
                    # DataFrame im Session State speichern
                    st.session_state["search_results_df"] = pd.DataFrame(raw_data)

            except Exception as e:
                st.error(f"Search failed: {e}")

    # --- EDITABLE TABLE AREA ---
    if "search_results_df" in st.session_state:
        df_to_edit = st.session_state["search_results_df"]

        # DIAGNOSE: Wenn die Spalte hier nicht steht, ist sie nicht im DF
        # st.write("Spalten im DF:", df_to_edit.columns.tolist()) 

        st.subheader("Refine Metadata")
        
        column_config = {
            "Ticker": st.column_config.TextColumn(disabled=True),
            "Name": st.column_config.TextColumn(disabled=True),
            "Exchange": st.column_config.TextColumn(disabled=True),
            "Currency": st.column_config.TextColumn(disabled=True),
            "AssetClass": st.column_config.SelectboxColumn(
                "Asset Class", 
                options=st.session_state.get('ref_asset_classes', ['EQU', 'BON', 'LIQ', 'ALT']), 
                required=True
            ),
            "Industry": st.column_config.TextColumn("Industry (Editable)"),
            "Sector": st.column_config.TextColumn("Sector (Yahoo)", disabled=True),
            "Sector_GICS": st.column_config.SelectboxColumn(
                "Sector GICS", options=st.session_state.get('ref_sectors', []), required=True
            ),
            "Country": st.column_config.TextColumn("Country (Editable)"),
            "Region": st.column_config.SelectboxColumn(
                "Region", options=st.session_state.get('ref_regions', []), required=True
            ),
            "InstrumentType_Raw": st.column_config.TextColumn("Type (Yahoo)", disabled=True),
            "InstrumentType": st.column_config.SelectboxColumn(
                "Instrument Type", options=st.session_state.get('ref_instr_types', []), required=True
            ),
            "Vol (7d Avg)": st.column_config.NumberColumn(disabled=True, format="%d")
        }

        # Falls der Editor die Spalte versteckt, erzwingen wir die Anzeige:
        edited_df = st.data_editor(
            df_to_edit,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key="ticker_editor_final" # Neuer Key für den Editor
        )
        
        if st.button("Accept Data"):
            st.success("Metadata refined!")
            st.dataframe(edited_df)
