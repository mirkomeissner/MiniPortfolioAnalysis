import streamlit as st
from .database import (
    db_get_user_profile, 
    db_approve_user,
    auth_login,
    auth_register,
    auth_logout,
    auth_update_user,
    check_existing_email
)
from types import SimpleNamespace



# --- AUTH FUNCTIONS ---
from types import SimpleNamespace
# Importiere hier deine Mail-Funktion (z.B. aus mailer.py)
# from mailer import send_duplicate_info_mail 

def register_user(email, password, username):
    """
    Handles user registration with a stealth check for existing emails 
    to prevent user enumeration while maintaining a good UX.
    """
    try:
        # 1. Pre-check: Does the email already exist in our public.users table?
        if check_existing_email(email):
            
            # --- INSERT EMAIL SENDING HERE ---
            # This is the perfect spot because we know the user exists, 
            # but we haven't told the UI yet.
            try:
                # send_duplicate_info_mail(email)
                pass # Replace 'pass' with your function call
            except Exception as mail_err:
                # We log the mail error silently to console
                print(f"Silent mail log: Failed to send info mail to {email}: {mail_err}")
            # ----------------------------------

            # Logically, we act as if the registration was successful.
            return SimpleNamespace(user=True)

        # 2. Proceed with actual Supabase registration if email is new
        response = auth_register(email, password, username)
        
        if response.user:
            # Auto-approve if the email is listed in admin secrets
            if email in st.secrets.get("ADMIN_EMAILS", []):
                db_approve_user(response.user.id)
                
        return response

    except Exception as e:
        error_msg = str(e).lower()
        
        # Double check: if Supabase throws the error despite our pre-check
        if "already registered" in error_msg:
            # You could also trigger the mail here as a fallback
            return SimpleNamespace(user=True)
            
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
                    # 1. Login durchführen
                    auth_response = auth_login(email, pwd) 
                    
                    if auth_response and auth_response.session:
                        # 2. Token sichern
                        st.session_state["access_token"] = auth_response.session.access_token
                        user_id = auth_response.user.id
                        
                        # 3. Profil laden
                        profile = db_get_user_profile(user_id)
                        
                        if profile and profile.get("is_approved"):
                            st.session_state.update({
                                "logged_in": True,
                                "user_id": user_id,
                                "user_name": profile["username"],
                                "user_email": email,
                                "is_admin": email in st.secrets.get("ADMIN_EMAILS", [])
                            })
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            # Hier löschen wir den Token, weil der User zwar existiert, aber nicht rein darf
                            st.session_state.pop("access_token", None)
                            st.warning("⏳ Your account is pending admin approval.")
                            auth_logout()
                    
                except Exception as e:
                    # NUR WENN DER LOGIN-AUFRUF SELBST FEHLSCHLÄGT
                    st.session_state.pop("access_token", None)
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
                        st.rerun()
    
        if "reg_success_msg" in st.session_state:
            st.success(st.session_state["reg_success_msg"])
            del st.session_state["reg_success_msg"]
        
    return False

def logout():
    auth_logout()
    for key in ["logged_in", "user_id", "user_name", "user_email", "is_admin", "access_token"]:
        st.session_state.pop(key, None)
    st.rerun()

def user_settings_ui():
    st.title("User Settings")
    user_data = db_get_user_profile(st.session_state["user_id"])
    if not user_data: return

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Change Password")
        with st.form("change_pwd_form"):
            new_pwd = st.text_input("New Password", type="password")
            confirm_pwd = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password"):
                try:
                    auth_update_user({"password": new_pwd})
                    st.success("✅ Password updated successfully!")
                except Exception as e: 
                    st.error(f"❌ Error: {e}")
 
    
    with col2:
        st.subheader("Edit Email Address")
        current_email = st.session_state.get("user_email", "") 
        pending_email = user_data.get("pending_email")

        st.write(f"Current eMail: `{current_email}`")

        if pending_email: st.info(f"🔄 **Email change in progress** to `{pending_email}`")      
        with st.form("edit_email_form"):
            new_email = st.text_input("New Email Address")
            if st.form_submit_button("Update Email"):
                if new_email and new_email != current_email:
                    try:
                        auth_update_user({"email": new_email})
                        st.success("✅ Email update initiated!")
                    except Exception as e: st.error(f"❌ Error: {e}")


