import streamlit as st
from supabase import create_client, Client

# 1. Setup Supabase Connection (via st.secrets)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# 2. Authentication Logic (Multi-User)
def check_password():
    """Returns True if the user has supplied a correct username and password."""
    
    def login_form():
        """Form to enter credentials"""
        with st.form("Login"):
            st.subheader("Login required")
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                # Retrieve users from secrets (stored as a dictionary)
                # Format in secrets.toml:
                # [credentials]
                # admin = "password123"
                # analyst = "finance456"
                credentials = st.secrets["credentials"]
                
                if user in credentials and pwd == credentials[user]:
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = user
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")

    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        login_form()
        return False
    
    return True

# 3. Helper function to fetch reference data
@st.cache_data(ttl=600)  # Cache data for 10 minutes to save API calls
def get_ref_data(table_name):
    try:
        query = supabase.table(table_name).select("Code, Label").execute()
        return {item['Label']: item['Code'] for item in query.data}
    except Exception as e:
        st.error(f"Error loading {table_name}: {e}")
        return {}

# 4. Main App (displayed only after successful login)
if check_password():
    st.sidebar.write(f"Logged in as: **{st.session_state['user_name']}**")
    
    st.title("🏦 Asset Manager")
    st.subheader("Create new record in AssetStaticData")

    # Load dynamic data from reference tables
    asset_classes = get_ref_data("RefAssetClass")
    regions = get_ref_data("RefRegion")
    sectors = get_ref_data("RefSector")

    # Display form if reference data was loaded successfully
    if asset_classes and regions and sectors:
        with st.form("asset_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                isin = st.text_input("ISIN (Primary Key)", placeholder="e.g. US0378331005")
                name = st.text_input("Asset Name", placeholder="e.g. Apple Inc.")
                ticker = st.text_input("Ticker", placeholder="AAPL")
                currency = st.text_input("Currency", value="USD", max_chars=3)

            with col2:
                # Dropdowns use Labels, but the logic handles the Codes
                selected_ac = st.selectbox("Asset Class", options=list(asset_classes.keys()))
                selected_reg = st.selectbox("Region", options=list(regions.keys()))
                selected_sec = st.selectbox("Sector", options=list(sectors.keys()))
                price_source = st.text_input("Price Source", value="Yahoo Finance")

            submitted = st.form_submit_button("Insert Asset")

            if submitted:
                if isin and name:
                    # Prepare payload (case-sensitive mapping to SQL schema)
                    new_row = {
                        "ISIN": isin,
                        "Name": name,
                        "Ticker": ticker,
                        "Currency": currency,
                        "PriceSource": price_source,
                        "AssetClassCode": asset_classes[selected_ac],
                        "RegionCode": regions[selected_reg],
                        "SectorCode": sectors[selected_sec]
                    }

                    # Execute Insert in Supabase
                    try:
                        supabase.table("AssetStaticData").insert(new_row).execute()
                        st.success(f"✅ Successfully added: {name} ({isin})")
                    except Exception as e:
                        st.error(f"❌ Database Error: {e}")
                else:
                    st.warning("Please provide both ISIN and Name!")
    else:
        st.error("Could not load reference data. Please check Supabase connection.")

    # Sidebar Logout
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["user_name"] = None
        st.rerun()
