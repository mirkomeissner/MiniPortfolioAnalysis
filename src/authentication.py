def check_password():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state["logged_in"]:
        return True

    st.title("Welcome to Asset Manager")
    
    with st.form("Login"):
        user = st.text_input("Username").strip()
        pwd = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            # 1. Check if user is even allowed (Admin control)
            allowed_users = st.secrets.get("allowed_users", [])
            if user not in allowed_users:
                st.error("❌ User not authorized by Admin.")
                return False
            
            # 2. Block empty passwords
            if not pwd:
                st.warning("⚠️ Please enter a password.")
                return False

            profile = get_user_profile(user)
            
            if profile:
                # Existing user: Compare hashes
                if profile["password_hash"] == hash_password(pwd):
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = user
                    st.rerun()
                else:
                    st.error("❌ Invalid password")
            else:
                # First time login: User in Secrets but not in DB
                # Force a minimum length for the first password
                if len(pwd) < 4:
                    st.error("❌ Password must be at least 4 characters long.")
                    return False
                
                set_user_password(user, pwd)
                st.success(f"Welcome {user}! Your password has been set.")
                st.session_state["logged_in"] = True
                st.session_state["user_name"] = user
                st.rerun()
    return False

