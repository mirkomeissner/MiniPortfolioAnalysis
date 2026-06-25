import streamlit as st

from src.database import get_user_holdings_reorganization_status, insert_user_holdings_reorganization


def _format_status_timestamp(timestamp):
    if timestamp is None:
        return "n/a"
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def _get_holdings_reorganization_ui_state(status):
    last_transaction_modification = status["last_transaction_modification"] if status else None
    last_reorganization = status["last_reorganization"] if status else None

    if last_transaction_modification is None:
        return {
            "visible": False,
            "label": None,
            "disabled": False,
            "info_text": None,
        }

    if last_reorganization is None:
        return {
            "visible": True,
            "label": "Reorganization of Holdings",
            "disabled": False,
            "info_text": "",
        }

    holdings_are_up_to_date = last_reorganization > last_transaction_modification
    return {
        "visible": True,
        "label": "holdings are up to date" if holdings_are_up_to_date else "Reorganization of Holdings",
        "disabled": holdings_are_up_to_date,
        "info_text": (
            f"Last modification of transactions was at {_format_status_timestamp(last_transaction_modification)} "
            f"and last reorganization was at {_format_status_timestamp(last_reorganization)}"
        ),
    }


def render_holdings_view():
    status = get_user_holdings_reorganization_status()
    ui_state = _get_holdings_reorganization_ui_state(status)

    if not ui_state["visible"]:
        return

    button_col, info_col = st.columns([1, 3])
    with button_col:
        if st.button(ui_state["label"], disabled=ui_state["disabled"]):
            try:
                insert_user_holdings_reorganization()
                st.success("Holdings reorganization saved.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save holdings reorganization: {exc}")

    with info_col:
        if ui_state["info_text"]:
            st.write(ui_state["info_text"])