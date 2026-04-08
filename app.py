import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Asset Manager", layout="wide")

# 2. Setup Supabase Connection
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# 3. Authentication Logic
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

def get_all_assets_with_labels():
    """Fetches records with joined labels and exact column ordering."""
    try:
        # Define columns to fetch including foreign key relations
        columns = (
            "ISIN, Name, Currency, Ticker, ClosedOn, created_at, created_by, "
            "RefPriceSource(Label), RefAssetClass(Label), RefRegion(Label), RefSector(Label)"
        )
        query = supabase.table("AssetStaticData").select(columns).execute()
        
        flattened_data = []
        for row in query.data:
            # We build the dictionary in the specific order you requested
            flattened_data.append({
                "ISIN": row.get("ISIN"),
                "Name": row.get("Name"),
                "Currency": row.get("Currency"),
                "Ticker": row.get("Ticker"),
                "PriceSource": row.get("RefPriceSource", {}).get("Label") if row.get("RefPriceSource") else None,
                "AssetClass": row.get("RefAssetClass", {}).get("Label") if row.get("RefAssetClass") else None,
                "Region": row.get("RefRegion", {}).get("Label") if row.get("RefRegion") else None,
                "Sector": row.get("RefSector", {}).get("Label") if row.get("RefSector") else None,
                "ClosedOn": row.get("ClosedOn"),
                "created_at": row.get("created_at"),
                "created_by": row.get("created_by")
            })
        return flattened_data
    except Exception as e:
        st.error(f"Error fetching assets: {e}")
        return []

# 5. Main App Logic
if check_password():
    st.sidebar.write(f"Logged in as: **{st.session_state['user_name']}**")
    menu = st.sidebar.selectbox("Menu", ["Home", "AssetStaticData"])
    
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

    if menu == "Home":
        st.title("Welcome")
        st.write("Please select an option from the menu on the left.")

    elif menu == "AssetStaticData":
        if "view" not in st.session_state:
            st.session_state["view"] = "list"

        if st.session_state["view"] == "list":
            st.title("AssetStaticData")
            
            if st.button("➕ New ISIN"):
                st.session_state["rows"] = [{"ISIN": "", "Name": "", "Ticker": "", "Currency": "USD", "AssetClass": "", "Region": "", "Sector": "", "PriceSource": ""}]
                st.session_state["view"] = "form"
                st.rerun()

            data = get_all_assets_with_labels()
            if data:
                st.dataframe(data, use_container_width=True)
            else:
                st.info("No data found.")

        elif st.session_state["view"] == "form":
            st.title("Create New Assets")
            
            # Fetch all reference dictionaries
            ac_dict = get_ref_data("RefAssetClass")
            reg_dict = get_ref_data("RefRegion")
            sec_dict = get_ref_data("RefSector")
            ps_dict = get_ref_data("RefPriceSource")

            if all([ac_dict, reg_dict, sec_dict, ps_dict]):
                # Table Header Adjustment for new PriceSource field
                header_cols = st.columns([1.5, 2, 0.8, 0.8, 1.5, 1.5, 1.5, 1.5, 0.5])
                headers = ["ISIN", "Name", "Ticker", "Curr", "Price Source", "Asset Class", "Region", "Sector", ""]
                for col, label in zip(header_cols, headers):
                    col.write(f"**{label}**")

                rows_to_delete = []
                for idx, row in enumerate(st.session_state["rows"]):
                    cols = st.columns([1.5, 2, 0.8, 0.8, 1.5, 1.5, 1.5, 1.5, 0.5])
                    
                    st.session_state["rows"][idx]["ISIN"] = cols[0].text_input("ISIN", value=row["ISIN"], key=f"isin_{idx}", label_visibility="collapsed")
                    st.session_state["rows"][idx]["Name"] = cols[1].text_input("Name", value=row["Name"], key=f"name_{idx}", label_visibility="collapsed")
                    st.session_state["rows"][idx]["Ticker"] = cols[2].text_input("Ticker", value=row["Ticker"], key=f"tick_{idx}", label_visibility="collapsed")
                    st.session_state["rows"][idx]["Currency"] = cols[3].text_input("Curr", value=row["Currency"], key=f"curr_{idx}", label_visibility="collapsed")
                    
                    st.session_state["rows"][idx]["PriceSource"] = cols[4].selectbox("PS", options=list(ps_dict.keys()), key=f"ps_{idx}", label_visibility="collapsed")
                    st.session_state["rows"][idx]["AssetClass"] = cols[5].selectbox("AC", options=list(ac_dict.keys()), key=f"ac_{idx}", label_visibility="collapsed")
                    st.session_state["rows"][idx]["Region"] = cols[6].selectbox("Reg", options=list(reg_dict.keys()), key=f"reg_{idx}", label_visibility="collapsed")
                    st.session_state["rows"][idx]["Sector"] = cols[7].selectbox("Sec", options=list(sec_dict.keys()), key=f"sec_{idx}", label_visibility="collapsed")
                    
                    if cols[8].button("🗑️", key=f"del_{idx}"):
                        rows_to_delete.append(idx)

                if rows_to_delete:
                    for i in reversed(rows_to_delete):
                        st.session_state["rows"].pop(i)
                    st.rerun()

                st.markdown("---")
                col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
                
                if col_btn1.button("➕ Add Row"):
                    st.session_state["rows"].append({"ISIN": "", "Name": "", "Ticker": "", "Currency": "USD", "AssetClass": "", "Region": "", "Sector": "", "PriceSource": ""})
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
                            "ISIN": r["ISIN"],
                            "Name": r["Name"],
                            "Ticker": r["Ticker"],
                            "Currency": r["Currency"],
                            "PriceSource": ps_dict[r["PriceSource"]],
                            "AssetClassCode": ac_dict[r["AssetClass"]],
                            "RegionCode": reg_dict[r["Region"]],
                            "SectorCode": sec_dict[r["Sector"]],
                            "created_by": st.session_state["user_name"] # Logged in user
                        })
                    
                    if valid and payload:
                        try:
                            supabase.table("AssetStaticData").insert(payload).execute()
                            st.success("✅ Bulk Insert Successful!")
                            st.session_state["view"] = "list"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Database Error: {e}")
                
                if col_btn3.button("Cancel"):
                    st.session_state["view"] = "list"
                    st.rerun()
