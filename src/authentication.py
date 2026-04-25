import streamlit as st
from supabase import create_client, Client
# Importiere die neuen Funktionen aus der database.py
from .database import get_user_by_id, get_admin_client

# --- CLIENT INITIALIZATION ---

@st.cache_resource
def get_supabase_client() -> Client:
    """Standard client for normal users (honors RLS)"""
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

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
                # Nutzt jetzt den admin_client aus database.py
                admin_supabase = get_admin_client() 
                admin_supabase.table("users").update({"is_approved": True}).eq("id", user_id).execute()

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
                    
                    if auth_response.session:
                        # WICHTIG: Token für database.py speichern
                        st.session_state["access_token"] = auth_response.session.access_token
                        
                        user_id = auth_response.user.id
                        
                        # Nutzt jetzt die zentrale Funktion aus database.py
                        profile_data = get_user_by_id(user_id)
                        
                        if profile_data and profile_data.get("is_approved"):
                            # Set session states
                            st.session_state["logged_in"] = True
                            st.session_state["user_id"] = user_id
                            st.session_state["user_name"] = profile_data["username"]
                            st.session_state["user_email"] = email
                            
                            # Admin Check
                            admin_list = st.secrets.get("ADMIN_EMAILS", [])
                            st.session_state["is_admin"] = email in admin_list
                            
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.warning("⏳ Your account is pending admin approval.")
                            supabase.auth.sign_out()
                            if "access_token" in st.session_state:
                                del st.session_state["access_token"]
                    
                except Exception:
                    st.error("❌ Invalid email or password.")

    with tab2:
        st.subheader("Register")
        with st.form("Registration Form", clear_on_submit=True):
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
                        st.session_state["reg_success_msg"] = f"✅ Account created for {new_username}!"
                        if new_email in st.secrets.get("ADMIN_EMAILS", []):
                            st.session_state["reg_success_msg"] += " Admin access granted automatically."
                        st.rerun() 
    
        if "reg_success_msg" in st.session_state:
            st.success(st.session_state["reg_success_msg"])
            del st.session_state["reg_success_msg"] 
        
    return False


def logout():
    """Beendet die Session bei Supabase und räumt den Session State auf."""
    try:
        supabase.auth.sign_out()
    except Exception as e:
        st.error(f"Fehler beim Abmelden bei Supabase: {e}")
    
    # Alle relevanten Session States löschen
    keys_to_clear = ["logged_in", "user_id", "user_name", "user_email", "is_admin", "access_token"]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
            
    st.success("Erfolgreich abgemeldet!")
    st.rerun()


def user_settings_ui():
    st.title("User Settings")

    # Nutzt jetzt die zentrale Funktion aus database.py
    user_data = get_user_by_id(st.session_state["user_id"])
    
    if not user_data:
        st.error("Error when loading configuration.")
        return
    
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
        # Falls in users Tabelle vorhanden (optional je nach DB-Trigger)
        pending_email = user_data.get("pending_email")

        if pending_email:
            st.info(f"🔄 **Email change in progress**")
            st.write(f"From: `{current_email}`")
            st.write(f"To: `{pending_email}`")
            
            status = user_data.get("pending_email_status", 0)
            if status == 0:
                st.warning("Waiting for confirmation on both addresses...")
            elif status == 1:
                st.success("One address confirmed (1/2). One more to go!")

        else:        
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
