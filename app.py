import streamlit as st
from supabase import create_client, Client

# 1. Setup Supabase Connection (via st.secrets)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# 2. Passwort-Schutz Logik
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Bitte Passwort eingeben", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Bitte Passwort eingeben", type="password", on_change=password_entered, key="password")
        st.error("❌ Passwort falsch")
        return False
    return True

# 3. Hilfsfunktion zum Abrufen der Referenzdaten
@st.cache_data(ttl=600)  # Speichert die Daten für 10 Min, um API-Calls zu sparen
def get_ref_data(table_name):
    try:
        query = supabase.table(table_name).select("Code, Label").execute()
        return {item['Label']: item['Code'] for item in query.data}
    except Exception as e:
        st.error(f"Fehler beim Laden von {table_name}: {e}")
        return {}

# 4. Haupt-App (wird nur nach Login angezeigt)
if check_password():
    st.title("🏦 Asset Manager")
    st.subheader("Neuen Datensatz in AssetStaticData anlegen")

    # Lade die dynamischen Daten aus den Ref-Tabellen
    asset_classes = get_ref_data("RefAssetClass")
    regions = get_ref_data("RefRegion")
    sectors = get_ref_data("RefSector")

    # Falls Daten geladen wurden, zeige das Formular
    if asset_classes and regions and sectors:
        with st.form("asset_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                isin = st.text_input("ISIN (Primary Key)", placeholder="z.B. US0378331005")
                name = st.text_input("Asset Name", placeholder="z.B. Apple Inc.")
                ticker = st.text_input("Ticker", placeholder="AAPL")
                currency = st.text_input("Currency", value="USD", max_chars=3)

            with col2:
                # Dropdowns nutzen die Labels aus der DB, speichern aber die Codes
                selected_ac = st.selectbox("Asset Class", options=list(asset_classes.keys()))
                selected_reg = st.selectbox("Region", options=list(regions.keys()))
                selected_sec = st.selectbox("Sector", options=list(sectors.keys()))
                price_source = st.text_input("Price Source", value="Yahoo Finance")

            submitted = st.form_submit_button("Insert Asset")

            if submitted:
                if isin and name:
                    # Payload vorbereiten (Großschreibung beachten wie im SQL-Script!)
                    new_row = {
                        "ISIN": isin,
                        "Name": name,
                        "Ticker": ticker,
                        "Currency": currency,
                        "PriceSource": price_source,
                        "AssetClassCode": asset_classes[selected_ac],
                        "RegionCode": regions[selected_reg],
                        "SectorCode": sectors[selected_sec]
                    }

                    # Insert in Supabase
                    try:
                        supabase.table("AssetStaticData").insert(new_row).execute()
                        st.success(f"✅ Erfogreich hinzugefügt: {name} ({isin})")
                    except Exception as e:
                        st.error(f"❌ Fehler beim Speichern: {e}")
                else:
                    st.warning("Bitte ISIN und Name ausfüllen!")
    else:
        st.error("Konnte Referenzdaten nicht aus der Datenbank laden. Bitte prüfe die Supabase-Verbindung.")

    # Sidebar Logout
    if st.sidebar.button("Abmelden"):
        st.session_state["password_correct"] = False
        st.rerun()
