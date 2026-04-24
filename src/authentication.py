import streamlit as st
from supabase import create_client, Client

# --- CLIENT INITIALIZATION ---

@st.cache_resource
def get_supabase_client() -> Client:
    """Standard client for normal users (honors RLS)"""
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

@st.cache_resource
def get_admin_client() -> Client:
    """Admin client for bypass RLS (Service Role)"""
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])

supabase = get_supabase_client()

# --- AUTH FUNCTIONS ---

def register_user(email, password, username):
    try:
        # 1. Sign up user in Supabase Auth
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"username": username}}
        })

        if response.user:
            user_id = response.user.id
            admin_list = st.secrets.get("ADMIN_EMAILS", [])

            # 2. Check for automatic admin approval
            if email in admin_list:
                admin_supabase = get_admin_client() 
                # Update approved status via service role
                admin_supabase.table("users").update({"is_approved": True}).eq("id", user_id).execute()
                st.info(f"Admin-Account '{username}' was automatically activated.")

        return response
    except Exception as e:
        st.error(f"Error with registration: {e}")
        return None

def check_password():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state["logged_in"]:
        return True

    tab1, tab2 = st.tabs(["Login", "Create Account"])

    with tab1:
        st.subheader("Login")
        with st.form("Login Form"):
            email = st.text_input("Email").strip()
            pwd = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                try:
                    # Authenticate
                    auth_response = supabase.auth.sign_in_with_password({
                        "email": email, 
                        "password": pwd
                    })
                    user_id = auth_response.user.id
                    
                    # Fetch profile to check approval
                    profile = supabase.table("users").select("is_approved, username").eq("id", user_id).single().execute()
                    
                    if profile.data and profile.data.get("is_approved"):
                        # Set session states
                        st.session_state["logged_in"] = True
                        st.session_state["user_id"] = user_id
                        st.session_state["user_name"] = profile.data["username"]
                        st.session_state["user_email"] = email
                        
                        # Admin Check based on secrets
                        admin_list = st.secrets.get("ADMIN_EMAILS", [])
                        st.session_state["is_admin"] = email in admin_list
                        
                        st.success("Login successful!")
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

    return False

def user_settings_ui():
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
                else:
                    st.error("❌ Passwords must match and be at least 6 characters.")
    
    with col2:
        st.subheader("Edit Email Address")
        current_email = st.session_state.get("user_email", "") 
        
        with st.form("edit_email_form"):
            new_email = st.text_input("New Email Address", value=current_email)
            if st.form_submit_button("Update Email"):
                if new_email and new_email != current_email:
                    try:
                        supabase.auth.update_user({"email": new_email})
                        st.success("✅ Email update initiated!")
                        st.info("Please check your email to confirm the change.")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

