import streamlit as st
import yfinance as yf
import pandas as pd
# Wir importieren die Speicherfunktion aus deiner database.py
from src.database import supabase, save_asset_static_data

# --- 1. HILFSFUNKTIONEN ---

def get_ref_options_list(table_name):
    try:
        response = supabase.table(table_name).select("code, label").execute()
        if not response.data:
            return []
        return [f"{item['code']} ({item['label']})" for item in response.data]
    except Exception as e:
        st.error(f"Fehler beim Laden von {table_name}: {e}")
        return []

def get_country_mapping():
    try:
        response = supabase.table("country_region_mapping").select("country, region_code").execute()
        return {item['country']: item['region_code'] for item in response.data}
    except:
        return {}

def map_yahoo_to_ref(yahoo_sector):
    mapping = {
        "Technology": "45", "Financial Services": "40", "Healthcare": "35",
        "Consumer Cyclical": "25", "Consumer Defensive": "30", "Basic Materials": "15",
        "Energy": "10", "Industrials": "20", "Communication Services": "50",
        "Utilities": "55", "Real Estate": "60"
    }
    return mapping.get(yahoo_sector, None)

def map_yahoo_to_instrument_type(quote_type, symbol_name=""):
    mapping = {"EQUITY": "STO", "ETF": "ETF", "MUTUALFUND": "FUN", "BOND": "BON", "CURRENCY": "FX", "CRYPTOCURRENCY": "CRY"}
    res = mapping.get(str(quote_type).upper(), "STO")
    if any(word in str(symbol_name).upper() for word in ["ZERTIFIKAT", "CERTIFICATE", "WARRANT"]):
        return "CER"
    return res

def map_yahoo_to_asset_class(quote_type, symbol_name=""):
    name_up = str(symbol_name).upper()
    qt_up = str(quote_type).upper()
    if qt_up == "CURRENCY" or "MONEY MARKET" in name_up: return "LIQ"
    if qt_up == "BOND" or any(word in name_up for word in ["BOND", "RENTEN", "TREASURY"]): return "BON"
    if qt_up in ["CRYPTOCURRENCY", "COMMODITY"] or any(word in name_up for word in ["GOLD", "REIT"]): return "ALT"
    return "EQU"

# Diese Funktion bereitet die Daten vor und ruft die Datenbank-Funktion auf
def handle_save_request(row, isin):
    def clean_code(val):
        return val.split(" (")[0] if val and " (" in str(val) else val

    asset_entry = {
        "isin": isin,
        "name": row["Name"],
        "currency": row["Currency"],
        "ticker": row["Ticker"],
        "price_source": "YFN",
        "instrument_type": clean_code(row["InstrumentType"]),
        "asset_class_code": clean_code(row["AssetClass"]),
        "region_code": clean_code(row["Region"]),
        "sector_code": clean_code(row["Sector_GICS"]),
        "industry": row["Industry"],
        "country": row["Country"],
        "created_by": st.session_state.get('user_name', 'System')
    }

    try:
        save_asset_static_data(asset_entry)
        st.success(f"✅ {row['Ticker']} wurde erfolgreich als Stammdatum gespeichert!")
        st.balloons()
    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")

# --- 2. HAUPTFUNKTION ---

def ticker_search_view():
    st.title("🔍 Ticker Search & Edit")

    if 'ref_data_loaded' not in st.session_state:
        with st.spinner("Lade Referenzdaten..."):
            st.session_state['db_region_map'] = get_country_mapping()
            st.session_state['opt_asset'] = get_ref_options_list("ref_asset_class")
            st.session_state['opt_gics'] = get_ref_options_list("ref_sector")
            st.session_state['opt_region'] = get_ref_options_list("ref_region")
            st.session_state['opt_type'] = get_ref_options_list("ref_instrument_type")
            st.session_state['ref_data_loaded'] = True

    isin_input = st.text_input("ISIN eingeben", placeholder="z.B. US0378331005")
    search_button = st.button("Ticker suchen")

    if search_button and isin_input:
        with st.spinner("Suche läuft..."):
            try:
                search_results = yf.Search(isin_input).quotes
                if not search_results:
                    st.warning("Keine Ergebnisse.")
                else:
                    raw_data = []
                    for res in search_results:
                        symbol = res.get("symbol")
                        t = yf.Ticker(symbol)
                        info = t.info
                        name = info.get("longName") or res.get("longname") or "Unbekannt"
                        raw_type = res.get("quoteType") or info.get("quoteType") or "EQUITY"
                        
                        a_code = map_yahoo_to_asset_class(raw_type, name)
                        asset_val = next((s for s in st.session_state['opt_asset'] if s.startswith(a_code)), a_code)
                        
                        g_code = map_yahoo_to_ref(info.get("sector"))
                        gics_val = next((s for s in st.session_state['opt_gics'] if s.startswith(str(g_code))), str(g_code))
                        
                        r_code = st.session_state['db_region_map'].get(info.get("country"), "GLO")
                        reg_val = next((s for s in st.session_state['opt_region'] if s.startswith(r_code)), r_code)
                        
                        i_code = map_yahoo_to_instrument_type(raw_type, name)
                        type_val = next((s for s in st.session_state['opt_type'] if s.startswith(i_code)), i_code)

                        raw_data.append({
                            "Ticker": symbol,
                            "Name": name,
                            "Exchange": info.get("exchange"),
                            "Currency": info.get("currency"),
                            "Industry": info.get("industry"),
                            "Sector": info.get("sector"),
                            "Sector_GICS": gics_val,
                            "Country": info.get("country", "Unknown"),
                            "Region": reg_val,
                            "InstrumentType_Raw": raw_type,
                            "InstrumentType": type_val,
                            "AssetClass": asset_val,
                            "Vol (7d Avg)": int(t.history(period="7d")['Volume'].mean()) if not t.history(period="7d").empty else 0
                        })
                    st.session_state["search_results_df"] = pd.DataFrame(raw_data)
            except Exception as e:
                st.error(f"Suche fehlgeschlagen: {e}")

    if "search_results_df" in st.session_state:
        column_config = {
            "Ticker": st.column_config.TextColumn(disabled=True),
            "Name": st.column_config.TextColumn(disabled=True),
            "Exchange": st.column_config.TextColumn(disabled=True),
            "Currency": st.column_config.TextColumn(disabled=True),
            "Industry": st.column_config.TextColumn("Industry"),
            "Sector": st.column_config.TextColumn("Yahoo Sector", disabled=True),
            "Sector_GICS": st.column_config.SelectboxColumn("GICS", options=st.session_state['opt_gics'], required=True),
            "Country": st.column_config.TextColumn("Country"),
            "Region": st.column_config.SelectboxColumn("Region", options=st.session_state['opt_region'], required=True),
            "InstrumentType_Raw": None,
            "InstrumentType": st.column_config.SelectboxColumn("Type", options=st.session_state['opt_type'], required=True),
            "AssetClass": st.column_config.SelectboxColumn("Asset Class", options=st.session_state['opt_asset'], required=True),
            "Vol (7d Avg)": st.column_config.NumberColumn(disabled=True, format="%d")
        }

        edited_df = st.data_editor(
            st.session_state["search_results_df"],
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key="final_asset_editor",
            num_rows="fixed",
            selection_mode="single_row"
        )

        selection = st.session_state["final_asset_editor"].get("selection", {}).get("rows", [])

        if selection:
            selected_row_index = selection[0]
            selected_data = edited_df.iloc[selected_row_index]

            st.write("---")
            st.write(f"Ausgewählt für Import: **{selected_data['Ticker']}** ({selected_data['Name']})")
            
            # Hier war der Name falsch (save_asset_to_db -> handle_save_request)
            if st.button("Jetzt in Datenbank speichern", type="primary", use_container_width=True):
                handle_save_request(selected_data, isin_input)
        else:
            st.info("💡 Bitte wählen Sie links in der Tabelle eine Zeile aus (Häkchen), um den Import zu starten.")


