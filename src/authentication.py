--- DATEIPFAD: ./src/authentication.py ---
import streamlit as st
import hashlib
from src.database import supabase

def hash_password(password):
    """Erzeugt einen SHA-256 Hash des Passworts."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def get_user_profile(username):
    """Holt das Profil aus der Datenbank."""
    res = supabase.table("user_profiles").select("*").eq("username", username).execute()
    return res.data[0] if res.data else None

def set_user_password(username, password):
    """Speichert oder aktualisiert den Passwort-Hash."""
    p_hash = hash_password(password)
    supabase.table("user_profiles").upsert({
        "username": username,
        "password_hash": p_hash
    }).execute()

def check_password():
    """Zentrale Login-Logik."""
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state["logged_in"]:
        return True

    st.title("Login")
    
    with st.form("Login Form"):
        # .strip() entfernt versehentliche Leerzeichen am Ende
        user = st.text_input("Username").strip()
        pwd = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            # 1. Admin-Check via Secrets
            allowed_users = st.secrets.get("allowed_users", [])
            if user not in allowed_users:
                st.error("❌ User not authorized by Admin.")
                return False
            
            # 2. Pflichtfeld-Check (Verhindert leere Passwörter)
            if not pwd:
                st.warning("⚠️ Please enter a password.")
                return False

            profile = get_user_profile(user)
            
            if profile:
                # Bekannter User: Passwort-Hash vergleichen
                if profile["password_hash"] == hash_password(pwd):
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = user
                    st.rerun()
                else:
                    st.error("❌ Invalid password")
            else:
                # Neuer User (in Secrets, aber nicht in DB): Passwort setzen
                if len(pwd) < 4:
                    st.error("❌ For security, passwords must be at least 4 characters.")
                    return False
                
                set_user_password(user, pwd)
                st.success(f"Welcome {user}! Your initial password has been set.")
                st.session_state["logged_in"] = True
                st.session_state["user_name"] = user
                st.rerun()
                
    return False

def change_password_ui():
    """UI Komponente für die Passwort-Änderung (optional)."""
    st.subheader("Security Settings")
    with st.expander("Change Password"):
        with st.form("change_pwd"):
            new_pwd = st.text_input("New Password", type="password")
            confirm_pwd = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password"):
                if new_pwd == confirm_pwd and len(new_pwd) >= 4:
                    set_user_password(st.session_state["user_name"], new_pwd)
                    st.success("Password updated successfully!")
                else:
                    st.error("Passwords do not match or are too short.")


