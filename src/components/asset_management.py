import streamlit as st
import pandas as pd
from src.database import get_all_assets_with_labels
from .ticker_search import ticker_search_view

def asset_table_view():
    if st.session_state.get("view") == "search":
        if st.button("⬅ Back to List"):
            st.session_state["view"] = "list"
            st.rerun()
        ticker_search_view()
        
    else:
        st.title("Asset Static Data")
        
        # Action Bar
        col_btn, _ = st.columns([1, 4])
        if col_btn.button("➕ New ISIN", use_container_width=True):
            st.session_state["view"] = "search"
            st.rerun()

        # Fetch Data
        data = get_all_assets_with_labels()
        if not data:
            st.info("No records found in asset_static_data.")
            return

        df = pd.DataFrame(data)

        # --- FILTER SECTION ---
        st.write("---")
        exp = st.expander("Filter Assets", expanded=False)
        with exp:
            f_col1, f_col2, f_col3 = st.columns(3)
            
            # Dynamic Filters based on data content
            asset_classes = ["All"] + sorted(df["Asset Class"].dropna().unique().tolist())
            regions = ["All"] + sorted(df["Region"].dropna().unique().tolist())
            currencies = ["All"] + sorted(df["Currency"].dropna().unique().tolist())

            selected_class = f_col1.selectbox("Asset Class", asset_classes)
            selected_region = f_col2.selectbox("Region", regions)
            selected_curr = f_col3.selectbox("Currency", currencies)

        # Apply Filters to DataFrame
        filtered_df = df.copy()
        if selected_class != "All":
            filtered_df = filtered_df[filtered_df["Asset Class"] == selected_class]
        if selected_region != "All":
            filtered_df = filtered_df[filtered_df["Region"] == selected_region]
        if selected_curr != "All":
            filtered_df = filtered_df[filtered_df["Currency"] == selected_curr]

        # Display Stats & Table
        st.info(f"Showing {len(filtered_df)} of {len(df)} assets")
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

