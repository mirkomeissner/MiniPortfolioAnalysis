import datetime
import math

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.database import (
    get_all_assets_with_labels,
    get_daily_holdings,
    get_user_holdings_min_date,
)
from src.utils import apply_advanced_filters


def _build_asset_class_pie_html(grouped_values: pd.Series) -> str:
    total = float(grouped_values.sum())
    if total <= 0:
        return ""

    palette = [
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

    for idx, (label, value) in enumerate(grouped_values.items()):
        if value <= 0:
            continue

        angle = (float(value) / total) * 360.0
        end_angle = start_angle + angle
        large_arc = 1 if angle > 180 else 0
        color = palette[idx % len(palette)]

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

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("No valid User-ID found. Please log in again.")
        st.stop()

    raw_holdings = get_daily_holdings(user_id=user_id, holding_date=selected_date)
    if not raw_holdings:
        return

    holdings_df = pd.DataFrame(raw_holdings)
    relevant_isins = sorted({str(value).strip() for value in holdings_df.get("isin", pd.Series(dtype=str)).dropna().tolist() if str(value).strip()})
    asset_rows = get_all_assets_with_labels(relevant_isins)
    asset_df = pd.DataFrame(asset_rows)

    if not asset_df.empty:
        asset_df = asset_df[
            [
                column
                for column in [
                    "ISIN",
                    "Name",
                    "Ticker",
                    "Risk Currency",
                    "Type",
                    "Asset Class",
                    "Region",
                    "Sector",
                    "Industry",
                    "Country",
                ]
                if column in asset_df.columns
            ]
        ].rename(
            columns={
                "Name": "Asset Name",
                "Ticker": "Asset Ticker",
                "Risk Currency": "Asset Risk Currency",
                "Type": "Asset Type",
                "Region": "Asset Region",
                "Sector": "Asset Sector",
                "Industry": "Asset Industry",
                "Country": "Asset Country",
            }
        )

    merged_df = holdings_df.merge(asset_df, left_on="isin", right_on="ISIN", how="left") if not asset_df.empty else holdings_df.copy()
    if "ISIN" in merged_df.columns:
        merged_df = merged_df.drop(columns=["ISIN"])

    # Streamlit's dataframe renderer requires unique column names.
    merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()].copy()

    merged_df = merged_df.rename(
        columns={
            "user_id": "User ID",
            "account_code": "Account Code",
            "holding_date": "Holding Date",
            "isin": "ISIN",
            "quantity": "Quantity",
            "price_currency": "Price Currency",
            "price": "Price",
            "valuation_in_price_currency": "Valuation (Price Curr)",
            "exchange_rate_to_eur": "FX to EUR",
            "valuation_in_eur": "Valuation (EUR)",
        }
    )

    preferred_order = [
        "User ID",
        "Account Code",
        "Holding Date",
        "ISIN",
        "Quantity",
        "Price Currency",
        "Price",
        "Valuation (Price Curr)",
        "FX to EUR",
        "Valuation (EUR)",
    ]
    preferred_order.extend([
        "Asset Name",
        "Asset Ticker",
        "Asset Risk Currency",
        "Asset Type",
        "Asset Class",
        "Asset Region",
        "Asset Sector",
        "Asset Industry",
        "Asset Country",
    ])

    existing_cols = [column for column in preferred_order if column in merged_df.columns]
    merged_df = merged_df[existing_cols]

    if "Holding Date" in merged_df.columns:
        merged_df["Holding Date"] = pd.to_datetime(merged_df["Holding Date"])

    if "Holding Date" in merged_df.columns:
        merged_df = merged_df.sort_values(by=["Holding Date", "Valuation (EUR)"], ascending=[False, False])

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

    chart_df = filtered_df.copy()
    if "Asset Class" in chart_df.columns:
        chart_df["Asset Class"] = chart_df["Asset Class"].fillna("Unknown").replace("", "Unknown")
    else:
        chart_df["Asset Class"] = "Unknown"

    if "Valuation (EUR)" in chart_df.columns:
        chart_values = pd.to_numeric(chart_df["Valuation (EUR)"], errors="coerce").fillna(0)
    else:
        chart_values = pd.Series([0] * len(chart_df), index=chart_df.index)

    chart_data = (
        pd.DataFrame({"Asset Class": chart_df["Asset Class"], "Valuation (EUR)": chart_values})
        .groupby("Asset Class", as_index=True)["Valuation (EUR)"]
        .sum()
        .sort_values(ascending=False)
    )

    st.subheader("Asset Class Allocation")
    if chart_data.empty or float(chart_data.sum()) <= 0:
        st.info("No positive valuation available for the pie chart.")
    else:
        components.html(_build_asset_class_pie_html(chart_data), height=390, scrolling=False)


    