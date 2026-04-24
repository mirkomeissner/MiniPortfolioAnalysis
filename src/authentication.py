import streamlit as st
import hashlib
from src.database import (
    get_user_profile,
    set_user_password,
    get_user_email,
    update_user_email,
    create_user,
    get_user_by_username
)


def register_user(email, password, username):
    try:
        # Registriert den User bei Supabase Auth
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"username": username}}
        })
        return response
    except Exception as e:
        st.error(f"Error with registration: {e}")
        return None



def check_password():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state["logged_in"]:
        return True

    st.title("Login")
    
    with st.form("Login Form"):
        email = st.text_input("Email").strip() # Supabase Auth nutzt primär Email
        pwd = st.text_input("Passwort", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            try:
                # 1. Versuch den Login bei Supabase Auth
                auth_response = supabase.auth.sign_in_with_password({
                    "email": email, 
                    "password": pwd
                })
                
                user_id = auth_response.user.id
                
                # 2. Prüfen, ob der User in deiner public.users Tabelle 'approved' ist
                # Hier nutzen wir den Client, der jetzt im User-Kontext läuft
                profile = supabase.table("users").select("is_approved, username").eq("id", user_id).single().execute()
                
                if profile.data and profile.data.get("is_approved"):
                    st.session_state["logged_in"] = True
                    st.session_state["user_id"] = user_id
                    st.session_state["user_name"] = profile.data["username"]
                    st.success("Erfolgreich eingeloggt!")
                    st.rerun()
                else:
                    st.warning("⏳ Dein Account wartet noch auf die Freigabe durch den Admin.")
                    # Wir loggen ihn wieder aus, damit die Session nicht "halb" offen ist
                    supabase.auth.sign_out()
                    
            except Exception as e:
                st.error("❌ Login fehlgeschlagen: E-Mail oder Passwort falsch.")
                return False
    return False




    

def user_settings_ui():
    """UI component for managing user settings (password and email)."""
    st.title("User Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Change Password")
        with st.form("change_pwd_form"):
            new_pwd = st.text_input("New Password", type="password")
            confirm_pwd = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password"):
                if new_pwd == confirm_pwd and len(new_pwd) >= 4:
                    p_hash = hash_password(new_pwd)
                    try:
                        set_user_password(st.session_state["user_id"], p_hash)
                        st.success("✅ Password updated successfully!")
                    except Exception:
                        st.error("❌ Failed to update password.")
                elif len(new_pwd) < 4:
                    st.error("❌ Password must be at least 4 characters long.")
                else:
                    st.error("❌ Passwords do not match.")
    
    with col2:
        st.subheader("Edit Email Address")
        current_email = get_user_email(st.session_state["user_id"])
        with st.form("edit_email_form"):
            email = st.text_input("Email Address", value=current_email or "", placeholder="your.email@example.com")
            if st.form_submit_button("Update Email"):
                if email:
                    try:
                        update_user_email(st.session_state["user_id"], email)
                        st.success("✅ Email updated successfully!")
                    except Exception as e:
                        if "duplicate" in str(e).lower():
                            st.error("❌ This email address is already in use.")
                        else:
                            st.error(f"❌ Error updating email: {e}")
                else:
                    st.warning("⚠️ Email address cannot be empty.")

