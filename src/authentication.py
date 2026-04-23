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

def hash_password(password):
    """Generates a SHA-256 hash of the provided password."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def create_new_user(username, password):
    """
    Handles user provisioning. Checks if the user exists in 'users' 
    before attempting an insert to avoid Unique Constraint violations.
    """
    # 1. Check if the user already exists
    existing_id = get_user_by_username(username)
    
    if existing_id:
        # User exists, use the existing UUID
        new_id = existing_id
    else:
        # User does not exist, try to create
        new_id = create_user(username)
        if not new_id:
            # Race condition: another process created the user, fetch it
            new_id = get_user_by_username(username)
            if not new_id:
                st.error("Failed to create user.")
                return None
    
    # 2. Set the password hash
    p_hash = hash_password(password)
    try:
        set_user_password(new_id, p_hash)
    except Exception as e:
        st.error(f"Error setting password: {e}")
        return None
        
    return new_id

def check_password():
    """Main login logic. Handles authentication and JIT user provisioning."""
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state["logged_in"]:
        return True

    st.title("Login")
    
    with st.form("Login Form"):
        user = st.text_input("Username").strip()
        pwd = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            # Check against Admin-defined allowed users (Streamlit Secrets)
            allowed_users = st.secrets.get("allowed_users", [])
            if user not in allowed_users:
                st.error("❌ User not authorized by Admin.")
                return False
            
            if not pwd:
                st.warning("⚠️ Please enter a password.")
                return False

            # Retrieve profile from DB
            profile = get_user_profile(user)
            
            if profile and profile["password_hash"]:
                # Registered user: Compare hashes
                if profile["password_hash"] == hash_password(pwd):
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = user
                    st.session_state["user_id"] = profile["id"]
                    st.rerun()
                else:
                    st.error("❌ Invalid password")
            else:
                # User is authorized in Secrets but missing from DB or has no password
                if len(pwd) < 4:
                    st.error("❌ For security, passwords must be at least 4 characters.")
                    return False
                
                new_uuid = create_new_user(user, pwd)
                if new_uuid:
                    st.success(f"Welcome {user}! Profile initialized.")
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = user
                    st.session_state["user_id"] = new_uuid
                    st.rerun()
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

