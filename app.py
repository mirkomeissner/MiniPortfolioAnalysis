import streamlit as st
from supabase import create_client, Client

# 1. Setup Supabase Connection
# In a real app, use st.secrets for these!
url = "YOUR_SUPABASE_URL"
key = "YOUR_SUPABASE_SERVICE_ROLE_KEY"
supabase: Client = create_client(url, key)

st.title("🏦 Asset Manager")
st.subheader("Add new record to AssetStaticData")

# 2. Fetch Reference Data for Dropdowns
# This makes the app "smart" by pulling your SQL codes automatically
def get_ref_data(table_name):
    query = supabase.table(table_name).select("Code, Label").execute()
    return {item['Label']: item['Code'] for item in query.data}

asset_classes = get_ref_data("RefAssetClass")
regions = get_ref_data("RefRegion")
sectors = get_ref_data("RefSector")

# 3. The Input Form
with st.form("asset_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        isin = st.text_input("ISIN (Primary Key)", placeholder="e.g. US0378331005")
        name = st.text_input("Asset Name", placeholder="e.g. Apple Inc.")
        ticker = st.text_input("Ticker", placeholder="AAPL")
        currency = st.text_input("Currency", value="USD", max_chars=3)

    with col2:
        # Dropdowns using the Labels but saving the Codes
        selected_ac = st.selectbox("Asset Class", options=list(asset_classes.keys()))
        selected_reg = st.selectbox("Region", options=list(regions.keys()))
        selected_sec = st.selectbox("Sector", options=list(sectors.keys()))
        price_source = st.text_input("Price Source", value="Bloomberg")

    submitted = st.form_submit_button("Insert Asset")

    if submitted:
        # Prepare the data payload
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

        # 4. Insert into Supabase
        try:
            response = supabase.table("AssetStaticData").insert(new_row).execute()
            st.success(f"✅ Successfully added {name}!")
        except Exception as e:
            st.error(f"❌ Error: {e}")