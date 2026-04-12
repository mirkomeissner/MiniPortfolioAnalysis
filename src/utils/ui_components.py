import streamlit as st
import pandas as pd

def apply_advanced_filters(df: pd.DataFrame, session_prefix: str, custom_filter_logic: dict = None) -> pd.DataFrame:
    """
    Renders a unified Advanced Query Builder UI and returns the filtered DataFrame.
    
    :param df: The original DataFrame to filter.
    :param session_prefix: Unique prefix for session state keys (e.g., 'asset' or 'import').
    :param custom_filter_logic: Optional dict mapping column names to custom UI/logic functions.
    """
    rules_key = f"{session_prefix}_filter_rules"
    
    if rules_key not in st.session_state:
        st.session_state[rules_key] = []

    with st.expander("🛠 Advanced Query Builder", expanded=False):
        logic_mode = st.radio(
            "Combination Logic", 
            ["Match ALL (AND)", "Match ANY (OR)"], 
            horizontal=True, 
            key=f"{session_prefix}_logic"
        )
        
        c1, c2 = st.columns([1, 4])
        if c1.button("➕ Add Rule", key=f"{session_prefix}_add"):
            st.session_state[rules_key].append({"column": df.columns[0]})
        
        if c2.button("🗑 Clear All", key=f"{session_prefix}_clear"):
            st.session_state[rules_key] = []
            st.rerun()

        active_filters = []
        for i, rule in enumerate(st.session_state[rules_key]):
            r_col1, r_col2, r_col3 = st.columns([2, 3, 0.5])
            
            col_name = r_col1.selectbox(
                f"Column {i}", df.columns, 
                key=f"{session_prefix}_col_{i}"
            )
            
            # Use custom logic if provided (e.g., for Date/Status fields)
            if custom_filter_logic and col_name in custom_filter_logic:
                mask = custom_filter_logic[col_name](df, r_col2, i, session_prefix)
                if mask is not None:
                    active_filters.append(mask)
            else:
                # Standard Logic: Multiselect for unique values
                options = sorted(df[col_name].dropna().unique().astype(str).tolist())
                selected_vals = r_col2.multiselect(
                    f"Values {i}", options, 
                    key=f"{session_prefix}_val_{i}"
                )
                if selected_vals:
                    active_filters.append(df[col_name].astype(str).isin(selected_vals))

            if r_col3.button("❌", key=f"{session_prefix}_rem_{i}"):
                st.session_state[rules_key].pop(i)
                st.rerun()

    # Apply the masks
    if not active_filters:
        return df

    mask = active_filters[0]
    for m in active_filters[1:]:
        mask = (mask & m) if logic_mode == "Match ALL (AND)" else (mask | m)
    
    return df[mask]

