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
        
        # New ISIN Button
        if st.button("➕ New ISIN"):
            st.session_state["view"] = "search"
            st.rerun()

        # Fetch Data
        data = get_all_assets_with_labels()
        if not data:
            st.info("No records found.")
            return

        df = pd.DataFrame(data)

        # --- ADVANCED DYNAMIC FILTER SECTION ---
        st.write("---")
        with st.expander("🛠 Advanced Query Builder", expanded=True):
            
            # Global Logic Switch
            logic_mode = st.radio("Combination Logic", ["Match ALL (AND)", "Match ANY (OR)"], horizontal=True)
            
            # Initialize filter state if not exists
            if "filter_rules" not in st.session_state:
                st.session_state["filter_rules"] = []

            # Buttons to add/clear rules
            c1, c2 = st.columns([1, 4])
            if c1.button("➕ Add Rule"):
                st.session_state["filter_rules"].append({"column": df.columns[0], "value": ""})
            if c2.button("🗑 Clear All"):
                st.session_state["filter_rules"] = []
                st.rerun()

            # Render rules
            active_filters = []
            for i, rule in enumerate(st.session_state["filter_rules"]):
                r_col1, r_col2, r_col3 = st.columns([2, 3, 0.5])
                
                # Select column to filter
                col_name = r_col1.selectbox(f"Column {i+1}", df.columns, key=f"col_{i}")
                
                # Select unique values for that column
                options = sorted(df[col_name].dropna().unique().astype(str).tolist())
                val = r_col2.multiselect(f"Values {i+1}", options, key=f"val_{i}")
                
                # Remove rule button
                if r_col3.button("❌", key=f"rem_{i}"):
                    st.session_state["filter_rules"].pop(i)
                    st.rerun()
                
                if val:
                    active_filters.append(df[col_name].astype(str).isin(val))

        # --- APPLY FILTER LOGIC ---
        filtered_df = df.copy()
        if active_filters:
            if logic_mode == "Match ALL (AND)":
                # Combine using bitwise AND (&)
                final_mask = active_filters[0]
                for mask in active_filters[1:]:
                    final_mask &= mask
            else:
                # Combine using bitwise OR (|)
                final_mask = active_filters[0]
                for mask in active_filters[1:]:
                    final_mask |= mask
            
            filtered_df = df[final_mask]

        # Display result info and table
        st.info(f"Filtered Results: {len(filtered_df)} items found.")
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)


