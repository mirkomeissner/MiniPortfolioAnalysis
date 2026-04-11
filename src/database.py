import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase_client()

@st.cache_data(ttl=600)
def get_ref_options(table_name):
    """Zentrale Funktion für Select-Boxen (Code + Label)."""
    try:
        res = supabase.table(table_name).select("code, label").execute()
        return [f"{item['code']} ({item['label']})" for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Fehler bei Referenzdaten {table_name}: {e}")
        return []

@st.cache_data(ttl=3600)
def get_country_region_map():
    """Lädt das Mapping von Land zu Region."""
    res = supabase.table("country_region_mapping").select("country, region_code").execute()
    return {item['country']: item['region_code'] for item in res.data}

def save_asset_static_data(asset_data):
    return supabase.table("asset_static_data").insert(asset_data).execute()


def get_all_assets_with_labels():
    """Fetches records with joined labels and returns a flat list of dicts."""
    # 1. Initialize the variable at the very beginning to avoid NameError
    flattened_data = []
    
    try:
        # Define columns with foreign key relations
        columns = (
            "isin, name, currency, ticker, closed_on, created_at, created_by, "
            "ref_price_source(label), ref_asset_class(label), ref_region(label), ref_sector(label)"
        )
        
        query = supabase.table("asset_static_data").select(columns).execute()
        
        if query.data:
            for row in query.data:
                # 2. Build the ordered dictionary
                flattened_data.append({
                    "isin": row.get("isin"),
                    "name": row.get("name"),
                    "currency": row.get("currency"),
                    "ticker": row.get("ticker"),
                    "price_source": row.get("ref_price_source", {}).get("label") if row.get("ref_price_source") else None,
                    "asset_class": row.get("ref_asset_class", {}).get("label") if row.get("ref_asset_class") else None,
                    "region": row.get("ref_region", {}).get("label") if row.get("ref_region") else None,
                    "sector": row.get("ref_sector", {}).get("label") if row.get("ref_sector") else None,
                    "closed_on": row.get("closed_on"),
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
    response = supabase.table("transactions") \
        .select("*") \
        .eq("username", user) \
        .execute()
    return response.data



