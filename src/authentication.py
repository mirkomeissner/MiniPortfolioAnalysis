import streamlit as st
from .database import (
    db_get_user_profile, 
    db_approve_user,
    auth_login,
    auth_register,
    auth_logout,
    auth_update_user
)

supabase = get_client()

# --- AUTH FUNCTIONS ---

def register_user(email, password, username):
    try:
        response = auth_register(email, password, username)
        if response.user:
            if email in st.secrets.get("ADMIN_EMAILS", []):
                db_approve_user(response.user.id)
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
                    auth_res = auth_login(email, pwd)
                    if auth_res.session:
                        st.session_state["access_token"] = auth_res.session.access_token
                        profile = db_get_user_profile(auth_res.user.id)
                        
                        if profile and profile.get("is_approved"):
                            st.session_state.update({
                                "logged_in": True,
                                "user_id": auth_res.user.id,
                                "user_name": profile["username"],
                                "user_email": email,
                                "is_admin": email in st.secrets.get("ADMIN_EMAILS", [])
                            })
                            st.rerun()
                        else:
                            st.warning("⏳ Your account is pending admin approval.")
                            auth_logout()
                           
                except:
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

        if pending_email:
            st.info(f"🔄 **Email change in progress** to `{pending_email}`")
            st.write(f"From: `{current_email}`")	
            st.write(f"To: `{pending_email}`")
        else:        
            with st.form("edit_email_form"):
                new_email = st.text_input("New Email Address", value=current_email)
                if st.form_submit_button("Update Email"):
                    if new_email and new_email != current_email:
                        try:
                            supabase.auth.update_user({"email": new_email})
                            st.success("✅ Email update initiated!")
                        except Exception as e: st.error(f"❌ Error: {e}")


