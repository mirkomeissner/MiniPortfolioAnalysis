import datetime
import math

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.utils import apply_advanced_filters, fetch_holdings_date_range, fetch_holdings_df, fetch_holdings_summary


def get_last_selectable_holdings_date(today: datetime.date | None = None) -> datetime.date:
    reference_today = today or datetime.date.today()
    return reference_today - datetime.timedelta(days=1)


def resolve_selected_holdings_date(
    session_value,
    first_date: datetime.date,
    last_date: datetime.date,
) -> datetime.date:
    if not isinstance(session_value, datetime.date):
        return last_date
    if session_value < first_date or session_value > last_date:
        return last_date
    return session_value


def get_user_holdings_min_date(user_id: str | None = None):
    if not user_id:
        return None
    return fetch_holdings_date_range(user_id).get("first_date")


def _build_asset_class_pie_html(grouped_values: pd.Series, color_by_label: dict | None = None) -> str:
    total = float(grouped_values.sum())
    if total <= 0:
        return ""

    fallback_palette = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]

    cx = 160
    cy = 160
    radius = 120
    start_angle = -90.0
    slices = []
    legend_items = []
    color_by_label = color_by_label or {}

    for idx, (label, value) in enumerate(grouped_values.items()):
        if value <= 0:
            continue

        angle = (float(value) / total) * 360.0
        end_angle = start_angle + angle
        large_arc = 1 if angle > 180 else 0
        color = color_by_label.get(label) or fallback_palette[idx % len(fallback_palette)]

        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)
        x1 = cx + radius * math.cos(start_rad)
        y1 = cy + radius * math.sin(start_rad)
        x2 = cx + radius * math.cos(end_rad)
        y2 = cy + radius * math.sin(end_rad)

        path = (
            f"M {cx} {cy} L {x1:.2f} {y1:.2f} "
            f"A {radius} {radius} 0 {large_arc} 1 {x2:.2f} {y2:.2f} Z"
        )
        slices.append(f'<path d="{path}" fill="{color}" stroke="#ffffff" stroke-width="2"></path>')
        legend_items.append(
            f"""
            <div style=\"display:flex;align-items:center;gap:8px;margin-bottom:6px;\">
                <span style=\"width:12px;height:12px;border-radius:50%;background:{color};display:inline-block;\"></span>
                <span style=\"flex:1;\">{label}</span>
                <strong>{float(value):,.2f}</strong>
            </div>
            """
        )
        start_angle = end_angle

    legend_html = "".join(legend_items)
    svg_html = "".join(slices)

    return f"""
    <div style=\"display:grid;grid-template-columns:minmax(280px, 340px) 1fr;gap:1rem;align-items:center;\">
      <div style=\"display:flex;justify-content:center;\">
        <svg viewBox=\"0 0 320 320\" width=\"320\" height=\"320\" role=\"img\" aria-label=\"Asset class pie chart\">
          <circle cx=\"160\" cy=\"160\" r=\"120\" fill=\"#f7f7f7\"></circle>
          {svg_html}
          <circle cx=\"160\" cy=\"160\" r=\"54\" fill=\"#ffffff\"></circle>
          <text x=\"160\" y=\"154\" text-anchor=\"middle\" font-size=\"18\" font-weight=\"700\" fill=\"#222222\">Total</text>
          <text x=\"160\" y=\"178\" text-anchor=\"middle\" font-size=\"16\" fill=\"#666666\">{total:,.2f}</text>
        </svg>
      </div>
      <div>
        {legend_html}
      </div>
    </div>
    """


def render_holdings_view():
    """Render holdings screen controls."""
    st.title("Holdings")

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("No valid User-ID found. Please log in again.")
        st.stop()

    first_date = get_user_holdings_min_date(user_id)
    last_date = get_last_selectable_holdings_date(datetime.date.today())

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
    default_date = resolve_selected_holdings_date(default_date, first_date, last_date)
    st.session_state["holdings_selected_date"] = default_date

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

    merged_df = fetch_holdings_df(user_id=user_id, selected_date=selected_date)
    if merged_df.empty:
        return

    filtered_df = apply_advanced_filters(merged_df, session_prefix="holdings_list")

    st.write(f"Showing **{len(filtered_df)}** holdings for **{selected_date.isoformat()}**.")

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Holding Date": st.column_config.DateColumn(format="DD.MM.YYYY"),
            "Quantity": st.column_config.NumberColumn(format="%.4f"),
            "Price": st.column_config.NumberColumn(format="%.4f"),
            "Valuation (Price Curr)": st.column_config.NumberColumn(format="%.2f"),
            "FX to EUR": st.column_config.NumberColumn(format="%.6f"),
            "Valuation (EUR)": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    pie_dimension = st.selectbox(
        "Pie Chart Dimension",
        ["Asset Class", "Asset Type", "Asset Region", "Asset Sector", "Asset Risk Currency"],
        key="holdings_pie_dimension",
    )

    summary = fetch_holdings_summary(
        user_id=user_id,
        selected_date=selected_date,
        pie_dimension=pie_dimension,
    )
    chart_items = summary.get("items", [])
    chart_data = pd.Series(
        {item["label"]: item["valuation_eur"] for item in chart_items},
        dtype=float,
    )
    color_by_label = {
        item["label"]: item.get("color_hex")
        for item in chart_items
        if item.get("color_hex")
    }

    st.subheader(f"Allocation by {pie_dimension}")
    if chart_data.empty or float(chart_data.sum()) <= 0:
        st.info("No positive valuation available for the pie chart.")
    else:
        components.html(
            _build_asset_class_pie_html(chart_data, color_by_label=color_by_label),
            height=390,
            scrolling=False,
        )


    