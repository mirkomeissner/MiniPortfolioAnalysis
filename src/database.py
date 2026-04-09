import streamlit as st
from supabase import create_client, Client

def get_supabase_client() -> Client:
    """Initializes the Supabase client using secrets."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# Create a single instance to be used across the app
supabase = get_supabase_client()

@st.cache_data(ttl=600)
def get_ref_data(table_name):
    """Fetches reference data and returns a dictionary of Label: Code."""
    try:
        query = supabase.table(table_name).select("Code, Label").execute()
        return {item['Label']: item['Code'] for item in query.data}
    except Exception as e:
        st.error(f"Error loading {table_name}: {e}")
        return {}

def get_all_assets_with_labels():
    """Fetches records with joined labels and returns a flat list of dicts."""
    # 1. Initialize the variable at the very beginning to avoid NameError
    flattened_data = []
    
    try:
        # Define columns with foreign key relations
        columns = (
            "ISIN, Name, Currency, Ticker, ClosedOn, created_at, created_by, "
            "RefPriceSource(Label), RefAssetClass(Label), RefRegion(Label), RefSector(Label)"
        )
        
        query = supabase.table("AssetStaticData").select(columns).execute()
        
        if query.data:
            for row in query.data:
                # 2. Build the ordered dictionary
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
        
    except Exception as e:
        st.error(f"Error fetching assets: {e}")
        # Even if an error occurs, we return the empty list initialized above
        
    return flattened_data
    




def get_all_transactions():
    """Fetch all transactions for the current user from Supabase."""
    user = st.session_state.get('user_name')
    response = supabase.table("Transactions") \
        .select("*") \
        .eq("Username", user) \
        .execute()
    return response.data




