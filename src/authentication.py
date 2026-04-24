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
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase_client()


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

    # Tabs für Login und Registrierung
    tab1, tab2 = st.tabs(["Login", "Create Account"])

    with tab1:
        st.subheader("Login")
        with st.form("Login Form"):
            email = st.text_input("Email").strip()
            pwd = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                try:
                    auth_response = supabase.auth.sign_in_with_password({
                        "email": email, 
                        "password": pwd
                    })
                    user_id = auth_response.user.id
                    
                    # Abfrage des Profils (Dank RLS Policy 'view own profile' erlaubt)
                    profile = supabase.table("users").select("is_approved, username").eq("id", user_id).single().execute()
                    
                    if profile.data and profile.data.get("is_approved"):
                        st.session_state["logged_in"] = True
                        st.session_state["user_id"] = user_id
                        st.session_state["user_name"] = profile.data["username"]
                        st.success("Success!")
                        st.rerun()
                    else:
                        st.warning("⏳ Your account is pending admin approval.")
                        supabase.auth.sign_out()
                        
                except Exception:
                    st.error("❌ Invalid email or password.")

    with tab2:
        st.subheader("Register")
        with st.form("Registration Form"):
            new_email = st.text_input("Email (required)").strip()
            new_username = st.text_input("Username (required)").strip()
            new_pwd = st.text_input("Password", type="password")
            confirm_pwd = st.text_input("Confirm Password", type="password")
            reg_submit = st.form_submit_button("Register")

            if reg_submit:
                if not new_email or not new_username:
                    st.error("Email and Username are required.")
                elif new_pwd != confirm_pwd:
                    st.error("Passwords do not match.")
                elif len(new_pwd) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    res = register_user(new_email, new_pwd, new_username)
                    if res:
                        st.success("✅ Account created! Please wait for admin approval.")
                        st.info("You can try to log in once the admin has activated your account.")

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
                if new_pwd == confirm_pwd and len(new_pwd) >= 6:
                    try:
                        supabase.auth.update_user({"password": new_pwd})
                        st.success("✅ Password updated successfully!")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                elif len(new_pwd) < 6:
                    st.error("❌ Password must be at least 6 characters long.")
                else:
                    st.error("❌ Passwords do not match.")
    
    with col2:
        st.subheader("Edit Email Address")
        # Wir holen die aktuelle Email direkt aus der Session oder dem Profil
        current_email = st.session_state.get("user_email", "") 
        
        with st.form("edit_email_form"):
            new_email = st.text_input("New Email Address", value=current_email)
            
            if st.form_submit_button("Update Email"):
                if new_email and new_email != current_email:
                    try:
                        # Der offizielle Supabase Auth Weg
                        supabase.auth.update_user({"email": new_email})
                        st.success("✅ Email update initiated!")
                        st.info("Note: Depending on your Supabase settings, you might need to confirm the new email address.")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                else:
                    st.warning("⚠️ Please enter a different email address.")

