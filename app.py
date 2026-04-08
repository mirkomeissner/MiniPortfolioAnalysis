import streamlit as st
from supabase import create_client, Client

# 1. Page Configuration (Must be the first command)
st.set_page_config(page_title="Asset Manager", layout="wide")

# 2. Setup Supabase Connection
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# 3. Authentication Logic
def check_password():
    """Returns True if the user is authenticated."""
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

# 4. Data Fetching Functions
@st.cache_data(ttl=600)
def get_ref_data(table_name):
    """Fetches reference data for dropdowns."""
    try:
        query = supabase.table(table_name).select("Code, Label").execute()
        return {item['Label']: item['Code'] for item in query.data}
    except Exception as e:
        st.error(f"Error loading {table_name}: {e}")
        return {}

def get_all_assets():
    """Fetches all records from AssetStaticData."""
    try:
        query = supabase.table("AssetStaticData").select("*").execute()
        return query.data
    except Exception as e:
        st.error(f"Error fetching assets: {e}")
        return []

# 5. Main App Logic
if check_password():
    # Sidebar: User Info
    st.sidebar.write(f"Logged in as: **{st.session_state['user_name']}**")
    
    # Sidebar: Navigation Menu
    menu = st.sidebar.selectbox("Menu", ["Home", "AssetStaticData"])
    
    # Logout Button at the bottom of sidebar
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

    # --- PAGE: HOME ---
    if menu == "Home":
        st.title("Welcome")
        st.write("Please select an option from the menu on the left.")

    # --- PAGE: ASSET STATIC DATA ---
    elif menu == "AssetStaticData":
        # Initialize view state (Table view vs. Form view)
        if "view" not in st.session_state:
            st.session_state["view"] = "list"

        if st.session_state["view"] == "list":
            st.title("AssetStaticData")
            
            # Button to switch to "New ISIN" form
            if st.button("➕ New ISIN"):
                # Initialize rows for the bulk form
                st.session_state["rows"] = [{"ISIN": "", "Name": "", "Ticker": "", "Currency": "USD", "AssetClass": "", "Region": "", "Sector": ""}]
                st.session_state["view"] = "form"
                st.rerun()

            # Display the existing table data
            data = get_all_assets()
            if data:
                st.dataframe(data, use_container_width=True)
            else:
                st.info("No data found in AssetStaticData.")

        # --- VIEW: INPUT FORM (New ISIN) ---
        elif st.session_state["view"] == "form":
            st.title("Create New Assets")
            
            asset_classes = get_ref_data("RefAssetClass")
            regions = get_ref_data("RefRegion")
            sectors = get_ref_data("RefSector")

            if asset_classes and regions and sectors:
                # Table Header
                header_cols = st.columns([2, 2, 1, 1, 2, 2, 2, 0.5])
                headers = ["ISIN", "Name", "Ticker", "Curr", "Asset Class", "Region", "Sector", ""]
                for col, label in zip(header_cols, headers):
                    col.write(f"**{label}**")

                rows_to_delete = []
                for idx, row in enumerate(st.session_state["rows"]):
                    cols = st.columns([2, 2, 1, 1, 2, 2, 2, 0.5])
                    st.session_state["rows"][idx]["ISIN"] = cols[0].text_input("ISIN", value=row["ISIN"], key=f"isin_{idx}", label_visibility="collapsed")
                    st.session_state["rows"][idx]["Name"] = cols[1].text_input("Name", value=row["Name"], key=f"name_{idx}", label_visibility="collapsed")
                    st.session_state["rows"][idx]["Ticker"] = cols[2].text_input("Ticker", value=row["Ticker"], key=f"tick_{idx}", label_visibility="collapsed")
                    st.session_state["rows"][idx]["Currency"] = cols[3].text_input("Curr", value=row["Currency"], key=f"curr_{idx}", label_visibility="collapsed")
                    st.session_state["rows"][idx]["AssetClass"] = cols[4].selectbox("AC", options=list(asset_classes.keys()), key=f"ac_{idx}", label_visibility="collapsed")
                    st.session_state["rows"][idx]["Region"] = cols[5].selectbox("Reg", options=list(regions.keys()), key=f"reg_{idx}", label_visibility="collapsed")
                    st.session_state["rows"][idx]["Sector"] = cols[6].selectbox("Sec", options=list(sectors.keys()), key=f"sec_{idx}", label_visibility="collapsed")
                    
                    if cols[7].button("🗑️", key=f"del_{idx}"):
                        rows_to_delete.append(idx)

                if rows_to_delete:
                    for i in reversed(rows_to_delete):
                        st.session_state["rows"].pop(i)
                    st.rerun()

                # Action Buttons
                col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
                if col_btn1.button("➕ Add Row"):
                    st.session_state["rows"].append({"ISIN": "", "Name": "", "Ticker": "", "Currency": "USD", "AssetClass": "", "Region": "", "Sector": ""})
                    st.rerun()

                if col_btn2.button("🚀 Submit All", type="primary"):
                    payload = []
                    valid = True
                    for r in st.session_state["rows"]:
                        if not r["ISIN"] or not r["Name"]:
                            st.error("ISIN and Name are required!")
                            valid = False
                            break
                        payload.append({
                            "ISIN": r["ISIN"], "Name": r["Name"], "Ticker": r["Ticker"],
                            "Currency": r["Currency"], "PriceSource": "Yahoo Finance",
                            "AssetClassCode": asset_classes[r["AssetClass"]],
                            "RegionCode": regions[r["Region"]], "SectorCode": sectors[r["Sector"]]
                        })
                    
                    if valid and payload:
                        try:
                            supabase.table("AssetStaticData").insert(payload).execute()
                            st.success("✅ Success!")
                            st.session_state["view"] = "list" # Redirect back to table
                            st.rerun()
                        except Exception as e:
                            st.error(f"Database Error: {e}")
                
                if col_btn1.button("Cancel"):
                    st.session_state["view"] = "list"
                    st.rerun()
