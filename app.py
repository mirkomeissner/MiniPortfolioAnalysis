import streamlit as st
from supabase import create_client, Client

# 1. Konfiguration der Seite
st.set_page_config(page_title="Portfolio Manager", page_icon="📈")

# 2. Verbindung zu Supabase herstellen
# Diese Werte müssen in den Streamlit Cloud Secrets stehen!
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# 3. Passwort-Logik Funktionen
def check_password():
    """Gibt True zurück, wenn der Nutzer das korrekte Passwort eingegeben hat."""
    def password_entered():
        """Prüft das Passwort gegen das Secret."""
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Passwort aus dem Speicher löschen
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Erstmalige Anzeige des Login-Feldes
        st.text_input(
            "Bitte Passwort eingeben", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Passwort war falsch
        st.text_input(
            "Bitte Passwort eingeben", type="password", on_change=password_entered, key="password"
        )
        st.error("❌ Falsches Passwort")
        return False
    else:
        # Passwort korrekt
        return True

# 4. Hauptprogramm (wird nur ausgeführt, wenn Passwort korrekt ist)
if check_password():
    st.title("Asset Manager 🚀")
    st.write("Erfasse neue Assets für dein Portfolio.")

    # Eingabeformular
    with st.form("asset_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            asset_name = st.text_input("Asset Name (z.B. Bitcoin, Apple)")
            asset_type = st.selectbox("Typ", ["Aktie", "Krypto", "ETF", "Rohstoff"])
        
        with col2:
            ticker = st.text_input("Ticker Symbol (z.B. BTC, AAPL)")
            sector = st.text_input("Sektor (z.B. Tech, Finance)")

        submit_button = st.form_submit_button("In Datenbank speichern")

    # Logik zum Speichern
    if submit_button:
        if asset_name and ticker:
            data = {
                "asset_name": asset_name,
                "ticker": ticker,
                "asset_type": asset_type,
                "sector": sector
            }
            
            try:
                # Annahme: Deine Tabelle in Supabase heißt 'AssetStaticData'
                response = supabase.table("AssetStaticData").insert(data).execute()
                st.success(f"✅ {asset_name} wurde erfolgreich gespeichert!")
            except Exception as e:
                st.error(f"Fehler beim Speichern: {e}")
        else:
            st.warning("Bitte fülle mindestens Name und Ticker aus!")

    # Kleiner Bonus: Logout-Button oben rechts
    if st.sidebar.button("Log out"):
        st.session_state["password_correct"] = False
        st.rerun()

else:
    # Text, der angezeigt wird, wenn man nicht eingeloggt ist
    st.info("Willkommen! Bitte gib das Passwort ein, um Zugriff auf die Portfolio-Verwaltung zu erhalten.")
