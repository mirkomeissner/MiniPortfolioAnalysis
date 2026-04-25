import streamlit as st
import pandas as pd
from src.database import (
    get_all_accounts,
    save_account,
    update_account,
    delete_account
)


def accounts_settings_view():
    """Main entry point for accounts management. Handles routing between views."""
    current_view = st.session_state.get("view", "list")

    if current_view == "form":
        render_account_form()
    else:
        render_list_view()


def render_list_view():
    """Display list of all accounts with options to create, edit, or delete."""
    st.title("Accounts Settings")
    
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("User not logged in.")
        return
    
    # Navigation buttons
    col1, col2 = st.columns([1, 4])
    if col1.button("➕ New Account", use_container_width=True):
        st.session_state["view"] = "form"
        st.session_state["edit_account_code"] = None
        st.rerun()
    
    # Load accounts data
    accounts = get_all_accounts(user_id)
    
    if not accounts:
        st.info("No accounts found. Click 'New Account' to create one.")
        return
    
    # Convert to DataFrame for display
    df = pd.DataFrame(accounts)
    df = df.rename(columns={
        "account_code": "Account Code",
        "description": "Description"
    })
    
    st.info(f"Displaying {len(df)} account(s).")
    
    # Display accounts table
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    
    # Handle row selection
    if event.selection.rows:
        selected_index = event.selection.rows[0]
        st.session_state["edit_account_code"] = df.iloc[selected_index]["Account Code"]
        st.session_state["view"] = "form"
        st.rerun()


def render_account_form():
    """Display form to create or edit an account."""
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("User not logged in.")
        return
    
    edit_account_code = st.session_state.get("edit_account_code")
    is_edit = edit_account_code is not None
    
    # Navigation
    col_nav1, col_nav2 = st.columns([1, 4])
    if col_nav1.button("⬅ Back", use_container_width=True):
        st.session_state["view"] = "list"
        st.rerun()
    
    st.title("Edit Account" if is_edit else "New Account")
    
    # Load existing account data if editing
    existing_account = None
    if is_edit:
        accounts = get_all_accounts(user_id)
        existing_account = next((a for a in accounts if a["account_code"] == edit_account_code), None)
    
    # Form fields
    with st.form("account_form", clear_on_submit=False):
        # Account Code field (read-only when editing)
        if is_edit:
            st.text_input(
                "Account Code",
                value=existing_account["account_code"] if existing_account else "",
                disabled=True
            )
            account_code = existing_account["account_code"] if existing_account else ""
        else:
            account_code = st.text_input(
                "Account Code",
                value="",
                help="Unique identifier for this account (e.g., IB-001, DKB-Main)"
            )
        
        # Description field
        description = st.text_area(
            "Description",
            value=existing_account["description"] if (existing_account and existing_account.get("description")) else "",
            help="E.g., 'Interactive Brokers - Main Account'"
        )
        
        # Form actions
        col_submit, col_delete = st.columns([1, 1])
        
        submit_button = col_submit.form_submit_button(
            "✅ Save Account" if is_edit else "✅ Create Account",
            use_container_width=True,
            type="primary"
        )
        
        if submit_button:
            # Validation
            if not account_code or not account_code.strip():
                st.error("Account Code is required.")
            elif not description or not description.strip():
                st.error("Description is required.")
            else:
                try:
                    if is_edit:
                        # Update existing account
                        update_account(user_id, account_code, description.strip())
                        st.success("✅ Account updated successfully!")
                    else:
                        # Create new account
                        save_account(user_id, account_code.strip(), description.strip())
                        st.success("✅ Account created successfully!")
                    
                    # Reset and go back to list
                    st.session_state["view"] = "list"
                    st.session_state["edit_account_code"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving account: {str(e)}")
    
    # Delete button (only for edit view)
    if is_edit:
        st.divider()
        if st.button("🗑️ Delete Account", use_container_width=True, type="secondary"):
            st.session_state["show_delete_confirmation"] = True
        
        # Delete confirmation
        if st.session_state.get("show_delete_confirmation"):
            st.warning(f"⚠️ Are you sure you want to delete account '{account_code}'?")
            col_confirm1, col_confirm2 = st.columns([1, 1])
            
            if col_confirm1.button("Yes, Delete", use_container_width=True, type="secondary"):
                try:
                    delete_account(user_id, account_code)
                    st.success("✅ Account deleted successfully!")
                    st.session_state["view"] = "list"
                    st.session_state["edit_account_code"] = None
                    st.session_state["show_delete_confirmation"] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting account: {str(e)}")
            
            if col_confirm2.button("Cancel", use_container_width=True):
                st.session_state["show_delete_confirmation"] = False
                st.rerun()
