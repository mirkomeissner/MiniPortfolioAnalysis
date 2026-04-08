import streamlit as st
from supabase import create_client, Client

# 1. Setup Supabase Connection
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# 2. Authentication Logic
def check_password():
    def login_form():
        with st.form("Login"):
            st.subheader("Login required")
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                credentials = st.secrets["credentials"]
                if user in credentials and pwd == credentials[user]:
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = user
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")

    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        login_form()
        return False
    return True

# 3. Data Fetching
@st.cache_data(ttl=600)
def get_ref_data(table_name):
    try:
        query = supabase.table(table_name).select("Code, Label").execute()
        return {item['Label']: item['Code'] for item in query.data}
    except Exception as e:
        st.error(f"Error loading {table_name}: {e}")
        return {}

# 4. Main App
if check_password():
    st.title("🏦 Bulk Asset Manager")

    # Initialize the row list in session state if it doesn't exist
    if "rows" not in st.session_state:
        st.session_state["rows"] = [{"ISIN": "", "Name": "", "Ticker": "", "Currency": "USD", "AssetClass": "", "Region": "", "Sector": ""}]

    # Load reference data
    asset_classes = get_ref_data("RefAssetClass")
    regions = get_ref_data("RefRegion")
    sectors = get_ref_data("RefSector")

    if asset_classes and regions and sectors:
        
        # --- TABLE HEADER ---
        # We simulate a table using columns
        header_cols = st.columns([2, 2, 1, 1, 2, 2, 2, 0.5])
        headers = ["ISIN", "Name", "Ticker", "Curr", "Asset Class", "Region", "Sector", ""]
        for col, label in zip(header_cols, headers):
            col.write(f"**{label}**")

        # --- TABLE ROWS ---
        rows_to_delete = []

        for idx, row in enumerate(st.session_state["rows"]):
            cols = st.columns([2, 2, 1, 1, 2, 2, 2, 0.5])
            
            # Input fields update the session state directly via keys
            st.session_state["rows"][idx]["ISIN"] = cols[0].text_input("ISIN", value=row["ISIN"], key=f"isin_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["Name"] = cols[1].text_input("Name", value=row["Name"], key=f"name_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["Ticker"] = cols[2].text_input("Ticker", value=row["Ticker"], key=f"tick_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["Currency"] = cols[3].text_input("Curr", value=row["Currency"], key=f"curr_{idx}", label_visibility="collapsed")
            
            st.session_state["rows"][idx]["AssetClass"] = cols[4].selectbox("AC", options=list(asset_classes.keys()), key=f"ac_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["Region"] = cols[5].selectbox("Reg", options=list(regions.keys()), key=f"reg_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["Sector"] = cols[6].selectbox("Sec", options=list(sectors.keys()), key=f"sec_{idx}", label_visibility="collapsed")
            
            # Delete Button (Bin Icon)
            if cols[7].button("🗑️", key=f"del_{idx}"):
                rows_to_delete.append(idx)

        # Handle row deletion
        if rows_to_delete:
            for i in reversed(rows_to_delete):
                st.session_state["rows"].pop(i)
            st.rerun()

        # --- ACTIONS ---
        col_buttons = st.columns([1, 1, 4])
        
        if col_buttons[0].button("➕ Add Row"):
            st.session_state["rows"].append({"ISIN": "", "Name": "", "Ticker": "", "Currency": "USD", "AssetClass": "", "Region": "", "Sector": ""})
            st.rerun()

        if col_buttons[1].button("🚀 Submit All", type="primary"):
            # Prepare the payload
            payload = []
            valid = True
            
            for r in st.session_state["rows"]:
                if not r["ISIN"] or not r["Name"]:
                    st.error("Error: ISIN and Name are required for all rows.")
                    valid = False
                    break
                
                payload.append({
                    "ISIN": r["ISIN"],
                    "Name": r["Name"],
                    "Ticker": r["Ticker"],
                    "Currency": r["Currency"],
                    "PriceSource": "Yahoo Finance", # Default or add to row
                    "AssetClassCode": asset_classes[r["AssetClass"]],
                    "RegionCode": regions[r["Region"]],
                    "SectorCode": sectors[r["Sector"]]
                })
            
            if valid and payload:
                try:
                    supabase.table("AssetStaticData").insert(payload).execute()
                    st.success(f"✅ Successfully inserted {len(payload)} records!")
                    st.session_state["rows"] = [{"ISIN": "", "Name": "", "Ticker": "", "Currency": "USD", "AssetClass": "", "Region": "", "Sector": ""}] # Reset
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Database Error: {e}")

    # Sidebar Logout
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()
