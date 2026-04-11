import streamlit as st
import hashlib
from src.database import supabase

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def get_user_profile(username):
    res = supabase.table("user_profiles").select("*").eq("username", username).execute()
    return res.data[0] if res.data else None

def set_user_password(username, password):
    p_hash = hash_password(password)
    supabase.table("user_profiles").upsert({
        "username": username,
        "password_hash": p_hash
    }).execute()

def check_password():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state["logged_in"]:
        return True

    st.title("Welcome to Asset Manager")
    
    with st.form("Login"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            allowed_users = st.secrets.get("allowed_users", [])
            
            if user not in allowed_users:
                st.error("❌ User not authorized by Admin.")
                return False
            
            profile = get_user_profile(user)
            
            if profile:
                # User exists, check password
                if profile["password_hash"] == hash_password(pwd):
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = user
                    st.rerun()
                else:
                    st.error("❌ Invalid password")
            else:
                # First time login: User is in secrets but not in DB
                st.info(f"Welcome {user}! This is your first login. The password you just entered will be saved as your new password.")
                set_user_password(user, pwd)
                st.session_state["logged_in"] = True
                st.session_state["user_name"] = user
                st.rerun()
    return False

def change_password_ui():
    """Call this function inside a settings page or profile view."""
    st.subheader("Change Password")
    with st.form("change_pwd"):
        new_pwd = st.text_input("New Password", type="password")
        confirm_pwd = st.text_input("Confirm New Password", type="password")
        if st.form_submit_button("Update Password"):
            if new_pwd == confirm_pwd and len(new_pwd) > 5:
                set_user_password(st.session_state["user_name"], new_pwd)
                st.success("Password updated successfully!")
            else:
                st.error("Passwords do not match or are too short.")

