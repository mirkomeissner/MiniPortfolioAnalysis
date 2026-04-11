import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase_client()

@st.cache_data(ttl=600)
def get_ref_options(table_name):
    """Fetch reference codes and labels for dropdowns."""
    try:
        res = supabase.table(table_name).select("code, label").execute()
        return [f"{item['code']} ({item['label']})" for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Error loading reference data {table_name}: {e}")
        return []

@st.cache_data(ttl=3600)
def get_country_region_map():
    res = supabase.table("country_region_mapping").select("country, region_code").execute()
    return {item['country']: item['region_code'] for item in res.data}

def save_asset_static_data(asset_data):
    """Inserts a new asset record."""
    return supabase.table("asset_static_data").insert(asset_data).execute()

def update_asset_static_data(isin, updated_data):
    """Updates an existing asset record by ISIN."""
    return supabase.table("asset_static_data").update(updated_data).eq("isin", isin).execute()

def get_all_assets_with_labels():
    """Fetches full asset records including joined reference labels."""
    flattened_data = []
    try:
        # Added updated_at and updated_by to the query strings
        columns = (
            "isin, name, currency, ticker, industry, country, "
            "ref_price_source(label), ref_instrument_type(label), "
            "ref_asset_class(label), ref_region(label), ref_sector(label), "
            "closed_on, created_at, created_by, updated_at, updated_by"
        )
        
        query = supabase.table("asset_static_data").select(columns).execute()
        
        if query.data:
            for row in query.data:
                flattened_data.append({
                    "ISIN": row.get("isin"),
                    "Name": row.get("name"),
                    "Ticker": row.get("ticker"),
                    "Currency": row.get("currency"),
                    "Type": row.get("ref_instrument_type", {}).get("label") if row.get("ref_instrument_type") else None,
                    "Asset Class": row.get("ref_asset_class", {}).get("label") if row.get("ref_asset_class") else None,
                    "Region": row.get("ref_region", {}).get("label") if row.get("ref_region") else None,
                    "Sector": row.get("ref_sector", {}).get("label") if row.get("ref_sector") else None,
                    "Industry": row.get("industry"),
                    "Country": row.get("country"),
                    "Price Source": row.get("ref_price_source", {}).get("label") if row.get("ref_price_source") else None,
                    "Closed On": row.get("closed_on"),
                    "Created At": row.get("created_at"),
                    "Created By": row.get("created_by"),
                    "Updated At": row.get("updated_at"),
                    "Updated By": row.get("updated_by")
                })
    except Exception as e:
        st.error(f"Error fetching assets: {e}")
        
    return flattened_data

def get_all_transactions():
    user = st.session_state.get('user_name')
    response = supabase.table("transactions").select("*").eq("username", user).execute()
    return response.data

def get_asset_ref_options():
    """Fetches all assets in 'ISIN (Name)' format for dropdowns."""
    try:
        # Select isin and name from asset_static_data [cite: 76]
        res = supabase.table("asset_static_data").select("isin, name").execute()
        return [f"{item['isin']} ({item['name']})" for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Error loading assets for dropdown: {e}")
        return []

def get_account_ref_options(username):
    """Fetches user accounts in 'Code (Description)' format."""
    try:
        # Filter by username to show only relevant accounts [cite: 79, 81]
        res = supabase.table("accounts").select("account_code, description").eq("username", username).execute()
        return [f"{item['account_code']} ({item['description']})" for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Error loading accounts: {e}")
        return []

def save_transaction(transaction_data):
    """Inserts a new transaction record into the database."""
    # Insert data into the transactions table [cite: 80]
    return supabase.table("transactions").insert(transaction_data).execute()




