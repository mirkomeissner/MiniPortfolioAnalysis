import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from src.database import supabase

def get_country_mapping():
    """Fetch the mapping from Supabase and return as a dictionary."""
    try:
        response = supabase.table("country_region_mapping").select("country, region_code").execute()
        return {item['country']: item['region_code'] for item in response.data}
    except Exception as e:
        st.error(f"Error loading region mapping: {e}")
        return {}

# mapping from yahoo sectors to GICS sectors
def map_yahoo_to_ref(yahoo_sector):
    mapping = {
        "Technology": "45",
        "Financial Services": "40",
        "Healthcare": "35",
        "Consumer Cyclical": "25",
        "Consumer Defensive": "30",
        "Basic Materials": "15",
        "Energy": "10",
        "Industrials": "20",
        "Communication Services": "50",
        "Utilities": "55",
        "Real Estate": "60"
    }
    return mapping.get(yahoo_sector, None)


def map_yahoo_to_instrument_type(quote_type, symbol_name=""):
    """
    Maps Yahoo's quoteType to your custom instrument types.
    """
    # Standard-Mapping
    mapping = {
        "EQUITY": "STO",       # Aktien
        "ETF": "ETF",          # ETFs
        "MUTUALFUND": "FUN",   # Klassische Investmentfonds
        "BOND": "BON",         # Anleihen
        "CURRENCY": "FX",      # (Falls du Währungen hast)
        "CRYPTOCURRENCY": "CRY" # (Falls du Krypto hast)
    }
    
    # Ergebnis von Yahoo holen
    res = mapping.get(quote_type.upper(), "STO") # STO als Fallback
    
    # Sonderlogik für Zertifikate (Yahoo führt diese oft als EQUITY)
    # Hier hilft oft ein Blick in den Namen
    if any(word in symbol_name.upper() for word in ["ZERTIFIKAT", "CERTIFICATE", "KNOCK-OUT", "WARRANT"]):
        return "CER"
        
    return res

def ticker_search_view():
    """Main view for the Ticker Search feature."""
    st.title("🔍 Ticker Search via ISIN")
    st.write("Search for trading venues and master data using the ISIN.")

    # Load mapping into session state to avoid constant DB calls
    if 'db_region_map' not in st.session_state:
        st.session_state['db_region_map'] = get_country_mapping()
    
    region_map = st.session_state['db_region_map']

    # Input Area
    col1, col2 = st.columns([3, 1])
    with col1:
        isin_input = st.text_input("Enter ISIN", placeholder="e.g. US0378331005")
    with col2:
        st.write("##") # Spacer
        search_button = st.button("Search Ticker", use_container_width=True)

    if search_button and isin_input:
        with st.spinner(f"Searching for {isin_input}..."):
            try:
                # 1. Search via yfinance
                search_results = yf.Search(isin_input).quotes
                
                if not search_results:
                    st.warning("No tickers found for this ISIN.")
                else:
                    data_list = []
                    
                    for res in search_results:
                        symbol = res.get("symbol")
                        ticker_obj = yf.Ticker(symbol)
                        info = ticker_obj.info
                        
                        # Region Mapping Logic
                        country = info.get("country", "Unknown")
                        name = info.get("longName") or res.get("longname") or ""
                        
                        # Heuristic for ETFs/Global funds
                        if any(word in name.upper() for word in ["WORLD", "GLOBAL", "ALL COUNTRY"]):
                            mapped_region = "GLO"
                        elif "DEVELOPED" in name.upper():
                            mapped_region = "DEV"
                        else:
                            mapped_region = region_map.get(country, "GLO")

                        # Yahoo Sektor abrufen
                        yahoo_sector = info.get("sector")
                        # GICS Code über deine Funktion ermitteln
                        gics_code = map_yahoo_to_ref(yahoo_sector)


                        # Typ von Yahoo abrufen (z.B. 'EQUITY' oder 'ETF')
                        # Entweder aus der Suche oder aus den Ticker-Infos
                        raw_type = res.get("quoteType") or info.get("quoteType")
        
                        # Auf deine Kürzel mappen
                        instrument_type_code = map_yahoo_to_instrument_type(raw_type, info.get("longName", ""))

                        
                        # Volume calculation (last 7 days)
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=7)
                        hist = ticker_obj.history(start=start_date, end=end_date)
                        avg_volume = hist['Volume'].mean() if not hist.empty else 0
                        
                        # Collect data
                        data_list.append({
                            "Ticker": symbol,
                            "Name": name,
                            "Exchange": info.get("exchange"),
                            "Currency": info.get("currency"),
                            "Industry": info.get("industry"),
                            "Sector": info.get("sector"),
                            "Sector_GICS": gics_code,
                            "Country": country,
                            "Region": mapped_region,
                            "InstrumentType_Raw": raw_type,
                            "InstrumentType": instrument_type_code,
                            "Vol (7d Avg)": f"{avg_volume:,.0f}"
                        })
                    
                    # Display table
                    df = pd.DataFrame(data_list)
                    st.subheader("Results")
                    st.dataframe(df, use_container_width=True, hide_index=True)

            except Exception as e:
                st.error(f"Search failed: {e}")
