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
        res = supabase.schema("shared").table(table_name).select("code, label").execute()
        return [f"{item['code']} ({item['label']})" for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Error loading reference data {table_name}: {e}")
        return []

@st.cache_data(ttl=3600)
def get_country_region_map():
    res = supabase.schema("shared").table("country_region_mapping").select("country, region_code").execute()
    return {item['country']: item['region_code'] for item in res.data}

def save_asset_static_data(asset_data):
    """Inserts a new asset record."""
    return supabase.schema("shared").table("asset_static_data").insert(asset_data).execute()

def update_asset_static_data(isin, updated_data):
    """Updates an existing asset record by ISIN."""
    return supabase.schema("shared").table("asset_static_data").update(updated_data).eq("isin", isin).execute()

def get_missing_isins(isins: list) -> list:
    """
    Checks which ISINs from the provided list are NOT yet in the database.
    Returns a list of missing ISIN strings.
    """
    if not isins:
        return []
    
    try:
        # Query existing ISINs from the unique set of input ISINs
        res = supabase.schema("shared").table("asset_static_data") \
            .select("isin") \
            .in_("isin", isins) \
            .execute()
        
        existing_isins = {item['isin'] for item in res.data}
        return [i for i in isins if i not in existing_isins]
    except Exception as e:
        st.error(f"Error checking for missing ISINs: {e}")
        return []


def get_all_assets_with_labels():
    """Fetches full asset records including joined reference labels."""
    flattened_data = []
    try:
        # REMOVED the aliases (the "xxx_code:" part) to keep default names
        columns = (
            "isin, name, currency, ticker, industry, country, "
            "ref_price_source(label), "
            "ref_instrument_type(label), "
            "ref_asset_class(label), "
            "ref_region(label), "
            "ref_sector(label), "
            "closed_on, created_at, "
            "created_by:users!fk_static_created_by(username), "
            "updated_by:users!fk_static_updated_by(username), "
            "updated_at"
        )
        
        query = supabase.schema("shared").table("asset_static_data").select(columns).execute()
        
        if query.data:
            for row in query.data:
                # Now row.get("ref_instrument_type") will actually find data
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
                    "Created By": row.get("created_by", {}).get("username") if row.get("created_by") else None,
                    "Updated At": row.get("updated_at"),
                    "Updated By": row.get("updated_by", {}).get("username") if row.get("updated_by") else None
                })
    except Exception as e:
        st.error(f"Error fetching assets: {e}")
        
    return flattened_data


def get_all_transactions():
    user_id = st.session_state.get('user_id')
    if not user_id:
        return []

    # Alle Spalten der Haupttabelle plus die Joins explizit aufgelistet
    columns = (
        "user_id, "
        "id, "
        "account_code, "
        "isin, "
        "date, "
        "type_code, "
        "quantity, "
        "settle_amount, "
        "settle_currency, "
        "settle_fxrate, "
        "amount_eur, "
        "created_at, "
        "updated_at, "
        # Joins zu den Views im public-Schema
        "ref_transaction_type!fk_ref_type(label), "
        "ref_currencies!fk_transaction_ref_currency(label), "
        "asset_static_data!fk_transaction_isin(name)"
    )
    
    try:
        response = supabase.schema("public") \
            .table("transactions") \
            .select(columns) \
            .eq("user_id", user_id) \
            .execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching transactions: {e}")
        return []

def get_asset_ref_options():
    """Fetches all assets in 'ISIN (Name)' format for dropdowns."""
    try:
        # Select isin and name from asset_static_data [cite: 76]
        res = supabase.schema("shared").table("asset_static_data").select("isin, name").execute()
        return [f"{item['isin']} ({item['name']})" for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Error loading assets for dropdown: {e}")
        return []

def get_account_ref_options(user_id):
    """Fetches user accounts in 'Code (Description)' format."""
    try:
        # Filter by username to show only relevant accounts [cite: 79, 81]
        res = supabase.schema("public").table("accounts").select("account_code, description").eq("user_id", user_id).execute()
        return [f"{item['account_code']} ({item['description']})" for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Error loading accounts: {e}")
        return []

def get_next_transaction_count(user_id, isin, date_str):
    """Counts existing transactions for an ISIN and date to determine the next suffix."""
    try:
        # We query the transactions for the specific user, ISIN and date [cite: 80, 81]
        res = supabase.schema("public").table("transactions") \
            .select("id") \
            .eq("user_id", user_id) \
            .eq("isin", isin) \
            .eq("date", date_str) \
            .execute()
        
        return len(res.data) + 1
    except Exception as e:
        st.error(f"Error calculating transaction count: {e}")
        return 1


def get_existing_ids_for_bulk(user_id, isins, dates):
    """
    Fetches only the 'id' column for transactions matching user_id, ISINs and dates.
    """
    try:
        # Added user_id filter to ensure we only check the current user's transactions
        response = supabase.schema("public").table("transactions") \
            .select("id") \
            .eq("user_id", user_id) \
            .in_("isin", isins) \
            .in_("date", dates) \
            .execute()
        return [item['id'] for item in response.data]
    except Exception as e:
        print(f"Error fetching existing IDs: {e}")
        return []




def save_transaction(transaction_data):
    """Inserts a new transaction record into the database."""
    # Insert data into the transactions table [cite: 80]
    return supabase.schema("public").table("transactions").insert(transaction_data).execute()

def save_transactions_bulk(payload_list):
    """
    Saves multiple transactions in a single database call.
    Payload_list must be a list of dictionaries where each dict 
    represents a row in the 'transactions' table.
    """
    try:
        # The .insert() method accepts a list of objects for bulk insertion.
        # This is significantly faster than inserting row by row.
        response = supabase.schema("public").table("transactions").insert(payload_list).execute()
        
        # You can optionally return the response if you need to 
        # verify the inserted data.
        return response
    except Exception as e:
        # Re-raise the exception to be caught by the UI error handling
        print(f"Error during bulk transaction insert: {e}")
        raise e



def get_import_settings(user_id, account_code):
    """Fetches saved mapping for a specific user and account."""
    response = supabase.schema("public").table("user_import_settings")\
        .select("mapping_config")\
        .eq("user_id", user_id)\
        .eq("account_code", account_code)\
        .execute()
    return response.data[0]["mapping_config"] if response.data else None

def save_import_settings(user_id, account_code, config):
    """Saves or updates the mapping configuration."""
    payload = {
        "user_id": user_id,
        "account_code": account_code,
        "mapping_config": config
    }
    # upsert handles both insert and update based on primary key
    supabase.schema("public").table("user_import_settings").upsert(payload).execute()




