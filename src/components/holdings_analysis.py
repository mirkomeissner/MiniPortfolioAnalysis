import datetime
import streamlit as st

from src.database import get_user_holdings_min_date


def render_holdings_view():
    """Render holdings screen controls."""
    st.title("Holdings")

    first_date = get_user_holdings_min_date()
    last_date = datetime.date.today() - datetime.timedelta(days=1)

    if first_date is None:
        st.info("No holdings are available yet.")
        return

    if first_date > last_date:
        st.info(
            "No selectable holdings date is available yet. "
            "The earliest holdings date is after yesterday."
        )
        return

    default_date = st.session_state.get("holdings_selected_date")
    if not isinstance(default_date, datetime.date) or default_date < first_date or default_date > last_date:
        default_date = last_date

    selected_date = st.date_input(
        "Holdings Date",
        value=default_date,
        min_value=first_date,
        max_value=last_date,
        key="holdings_selected_date",
    )

    st.caption(
        f"Select a date between {first_date.isoformat()} and {last_date.isoformat()}."
    )
    st.write(f"Selected holdings date: {selected_date.isoformat()}")