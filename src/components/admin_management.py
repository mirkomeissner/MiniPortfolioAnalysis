import streamlit as st
from src.database import db_get_all_users, db_update_user_approval

def admin_approval_page():
    st.title("🛡️ Admin Console")
    st.subheader("User Management & Approvals")

    # Daten über die zentrale Datenbank-Funktion holen
    all_users = db_get_all_users()

    if not all_users:
        st.info("Keine registrierten User gefunden.")
        return

    # Tabs für bessere Übersicht
    tab_pending, tab_approved = st.tabs(["Wartend ⏳", "Freigeschaltet ✅"])

    with tab_pending:
        pending = [u for u in all_users if not u["is_approved"]]
        if not pending:
            st.success("Alle User sind freigeschaltet!")
        else:
            for user in pending:
                with st.expander(f"📌 {user['username']} ({user['email']})"):
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"Registriert am: {user['created_at']}")
                    if col2.button("Freischalten", key=f"approve_{user['id']}"):
                        db_update_user_approval(user['id'], True)
                        st.success(f"User {user['username']} freigeschaltet!")
                        st.rerun()

    with tab_approved:
        approved = [u for u in all_users if u["is_approved"]]
        for user in approved:
            is_admin = user['email'] in st.secrets.get("ADMIN_EMAILS", [])
            admin_label = " (Admin)" if is_admin else ""
            
            with st.expander(f"👤 {user['username']} ({user['email']}){admin_label}"):
                col1, col2 = st.columns([3, 1])
                col1.write(f"ID: `{user['id']}`")
                
                if not is_admin:
                    if col2.button("Sperren", key=f"block_{user['id']}", type="secondary"):
                        db_update_user_approval(user['id'], False)
                        st.warning(f"User {user['username']} gesperrt.")
                        st.rerun()
                else:
                    col2.info("Admin-Status")
