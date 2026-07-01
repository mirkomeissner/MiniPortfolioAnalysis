import streamlit as st
from .utils import (
    fetch_user_profile_via_backend,
    login_via_backend,
    logout_via_backend,
    register_user_via_backend,
    update_email_via_backend,
    update_password_via_backend,
    update_username_via_backend,
)




# --- AUTH FUNCTIONS ---

def register_user(email, password, username):
    try:
        return register_user_via_backend(
            email=email,
            password=password,
            username=username,
            admin_emails=st.secrets.get("ADMIN_EMAILS", []),
        )
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
                    auth_response = login_via_backend(email, pwd)
                    if auth_response.get("authenticated"):
                        if auth_response.get("is_approved"):
                            st.session_state.update({
                                "logged_in": True,
                                "user_id": auth_response.get("user_id"),
                                "user_name": auth_response.get("username"),
                                "user_email": auth_response.get("email") or email,
                                "access_token": auth_response.get("access_token"),
                                "is_admin": email.strip().lower() in {
                                    str(admin_email).strip().lower()
                                    for admin_email in st.secrets.get("ADMIN_EMAILS", [])
                                },
                            })
                            st.success("Login successful!")
                            st.rerun()

                        st.session_state.pop("access_token", None)
                        st.warning("⏳ Your account is pending admin approval.")
                    else:
                        st.session_state.pop("access_token", None)
                        st.error("❌ Invalid email or password.")
                except Exception:
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
    try:
        logout_via_backend()
    except Exception:
        pass
    for key in ["logged_in", "user_id", "user_name", "user_email", "is_admin", "access_token"]:
        st.session_state.pop(key, None)
    st.rerun()

def user_settings_ui():
    st.title("User Settings")
    user_data = fetch_user_profile_via_backend(st.session_state["user_id"])
    if not user_data: return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Change Password")
        with st.form("change_pwd_form"):
            new_pwd = st.text_input("New Password", type="password")
            confirm_pwd = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password"):
                try:
                    update_password_via_backend(new_pwd)
                    st.success("✅ Password updated successfully!")
                except Exception as e: 
                    st.error(f"❌ Error: {e}")
 
    
    with col2:
        st.subheader("Edit Username")
        current_username = st.session_state.get("user_name", user_data.get("username", ""))
        st.write(f"Current Username: `{current_username}`")

        with st.form("edit_username_form"):
            new_username = st.text_input("New Username", value=current_username)
            if st.form_submit_button("Update Username"):
                if new_username and new_username != current_username:
                    try:
                        update_username_via_backend(new_username)
                        st.session_state["user_name"] = new_username
                        st.success("✅ Username updated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                else:
                    st.warning("Please enter a different username.")

    with col3:
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
                        update_email_via_backend(new_email)
                        st.success("✅ Email update initiated!")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")


