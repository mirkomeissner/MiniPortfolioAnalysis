import streamlit as st
from src.authentication import get_admin_client

def admin_approval_page():
    st.title("🛡️ Admin Console")
    st.subheader("User Management & Approvals")

    # Admin-Client holen (nutzt Service Role Key)
    admin_supabase = get_admin_client()

    # 1. Alle Profile laden
    try:
        # Wir holen alle User, sortiert nach Erstellungsdatum
        response = admin_supabase.table("users").select("*").not_.is_("email_confirmed_at", "null").order("created_at", desc=True).execute()
        all_users = response.data
    except Exception as e:
        st.error(f"Fehler beim Laden der User: {e}")
        return

    if not all_users:
        st.info("Keine registrierten User gefunden.")
        return

    # 2. Tabs für bessere Übersicht
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
                        admin_supabase.table("users").update({"is_approved": True}).eq("id", user['id']).execute()
                        st.success(f"User {user['username']} freigeschaltet!")
                        st.rerun()

    with tab_approved:
        approved = [u for u in all_users if u["is_approved"]]
        for user in approved:
            # Check ob Admin (aus Secrets)
            is_admin = user['email'] in st.secrets.get("ADMIN_EMAILS", [])
            admin_label = " (Admin)" if is_admin else ""
            
            with st.expander(f"👤 {user['username']} ({user['email']}){admin_label}"):
                col1, col2 = st.columns([3, 1])
                col1.write(f"ID: `{user['id']}`")
                
                # Admins können nicht gesperrt werden (Sicherheit gegen Aussperren)
                if not is_admin:
                    if col2.button("Sperren", key=f"block_{user['id']}", type="secondary"):
                        admin_supabase.table("users").update({"is_approved": False}).eq("id", user['id']).execute()
                        st.warning(f"User {user['username']} gesperrt.")
                        st.rerun()
                else:
                    col2.info("Admin-Status")


                    
