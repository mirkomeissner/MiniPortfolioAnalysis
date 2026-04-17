import streamlit as st
import hashlib
from src.database import supabase

def hash_password(password):
    """Generates a SHA-256 hash of the provided password."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def get_user_profile(username):
    """
    Fetches the user profile and their password hash by joining 
    public.users and public.user_secrets.
    """
    # Join users and user_secrets via foreign key relationship
    res = supabase.table("users").select("id, username, user_secrets(password_hash)").eq("username", username).execute()
    
    if res.data:
        data = res.data[0]
        
        # Handle the joined result: user_secrets might be a list, a dict, or None
        secrets = data.get("user_secrets")
        p_hash = None
        
        if isinstance(secrets, list) and len(secrets) > 0:
            p_hash = secrets[0].get("password_hash")
        elif isinstance(secrets, dict):
            p_hash = secrets.get("password_hash")

        return {
            "id": data["id"],
            "username": data["username"],
            "password_hash": p_hash
        }
    return None

def set_user_password(user_id, password):
    """Updates or inserts the password hash in the user_secrets table."""
    p_hash = hash_password(password)
    # Use upsert to handle both first-time creation and password updates
    supabase.table("user_secrets").upsert({
        "user_id": user_id,
        "password_hash": p_hash
    }).execute()

def create_new_user(username, password):
    """
    Handles user provisioning. Checks if the user exists in 'users' 
    before attempting an insert to avoid Unique Constraint violations.
    """
    # 1. Check if the user already exists in the base 'users' table
    existing = supabase.table("users").select("id").eq("username", username).execute()
    
    if existing.data:
        # User exists, retrieve the existing UUID
        new_id = existing.data[0]["id"]
    else:
        # User does not exist, perform insert
        try:
            user_res = supabase.table("users").insert({"username": username}).execute()
            if user_res.data:
                new_id = user_res.data[0]["id"]
            else:
                return None
        except Exception as e:
            # Fallback if a race condition occurs (duplicate key error 23505)
            if "23505" in str(e):
                res = supabase.table("users").select("id").eq("username", username).execute()
                new_id = res.data[0]["id"]
            else:
                st.error(f"Database Error: {e}")
                raise e
        
    # 2. Link/Update the password in public.user_secrets
    set_user_password(new_id, password)
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

def change_password_ui():
    """UI component for updating the current user's password."""
    st.subheader("Security Settings")
    with st.expander("Change Password"):
        with st.form("change_pwd"):
            new_pwd = st.text_input("New Password", type="password")
            confirm_pwd = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password"):
                if new_pwd == confirm_pwd and len(new_pwd) >= 4:
                    # Update using the UUID from session state
                    set_user_password(st.session_state["user_id"], new_pwd)
                    st.success("Password updated successfully!")
                else:
                    st.error("Passwords do not match or are too short.")

