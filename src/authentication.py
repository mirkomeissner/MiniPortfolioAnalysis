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
    # We join users and user_secrets via the foreign key relationship
    res = supabase.table("users").select("id, username, user_secrets(password_hash)").eq("username", username).execute()
    
    if res.data:
        data = res.data[0]
        # Flatten the joined result for easier access
        return {
            "id": data["id"],
            "username": data["username"],
            "password_hash": data["user_secrets"]["password_hash"] if data.get("user_secrets") else None
        }
    return None

def set_user_password(user_id, password):
    """Updates the password hash in the user_secrets table."""
    p_hash = hash_password(password)
    # user_id is the UUID primary key in user_secrets
    supabase.table("user_secrets").upsert({
        "user_id": user_id,
        "password_hash": p_hash
    }).execute()

def create_new_user(username, password):
    """Helper to create a new user in both tables."""
    # 1. Create entry in public.users
    user_res = supabase.table("users").insert({"username": username}).execute()
    if user_res.data:
        new_id = user_res.data[0]["id"]
        # 2. Create entry in public.user_secrets
        set_user_password(new_id, password)
        return new_id
    return None

def check_password():
    """Main login logic adapted for UUID and two-table schema."""
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
            allowed_users = st.secrets.get("allowed_users", [])
            if user not in allowed_users:
                st.error("❌ User not authorized by Admin.")
                return False
            
            if not pwd:
                st.warning("⚠️ Please enter a password.")
                return False

            profile = get_user_profile(user)
            
            if profile and profile["password_hash"]:
                # Existing user: Compare hashes
                if profile["password_hash"] == hash_password(pwd):
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = user
                    st.session_state["user_id"] = profile["id"] # CRITICAL: Store the UUID!
                    st.rerun()
                else:
                    st.error("❌ Invalid password")
            else:
                # New user (In Secrets but not in DB)
                if len(pwd) < 4:
                    st.error("❌ For security, passwords must be at least 4 characters.")
                    return False
                
                new_uuid = create_new_user(user, pwd)
                if new_uuid:
                    st.success(f"Welcome {user}! Profile created.")
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = user
                    st.session_state["user_id"] = new_uuid # Store the new UUID
                    st.rerun()
    return False

def change_password_ui():
    """UI component using user_id from session state."""
    st.subheader("Security Settings")
    with st.expander("Change Password"):
        with st.form("change_pwd"):
            new_pwd = st.text_input("New Password", type="password")
            confirm_pwd = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password"):
                if new_pwd == confirm_pwd and len(new_pwd) >= 4:
                    # Use the UUID from session state
                    set_user_password(st.session_state["user_id"], new_pwd)
                    st.success("Password updated successfully!")
                else:
                    st.error("Passwords do not match or are too short.")

