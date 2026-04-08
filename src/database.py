import streamlit as st
from supabase import create_client, Client

def get_supabase_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase_client()

@st.cache_data(ttl=600)
def get_ref_data(table_name):
    query = supabase.table(table_name).select("Code, Label").execute()
    return {item['Label']: item['Code'] for item in query.data}

def get_all_assets_with_labels():
    columns = (
        "ISIN, Name, Currency, Ticker, ClosedOn, created_at, created_by, "
        "RefPriceSource(Label), RefAssetClass(Label), RefRegion(Label), RefSector(Label)"
    )
    query = supabase.table("AssetStaticData").select(columns).execute()
    # ... (flattening logic wie zuvor)
    return flattened_data
