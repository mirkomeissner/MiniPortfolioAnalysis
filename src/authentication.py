import streamlit as st

def check_password():
    def login_form():
        with st.form("Login"):
            st.subheader("Login required")
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if user in st.secrets["credentials"] and pwd == st.secrets["credentials"][user]:
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = user
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")

    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        login_form()
        return False
    return True
