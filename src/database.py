import streamlit as st
from supabase import create_client, Client

# --- HELPER FÜR AUTHENTIFIZIERUNG ---

def get_client() -> Client:
    """Gibt den vorkonfigurierten Client zurück (für Auth-Zwecke)."""
    return _get_client()

def get_admin_client() -> Client:
    """Admin client for bypass RLS (Service Role) - Nur für interne Zwecke."""
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])

def _get_client() -> Client:
    """
    Erstellt einen frischen Client und injiziert automatisch den 
    User-Token (JWT) aus dem Session State.
    """
    client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    
    # Priorität 1: Token aus session_state (von authentication.py gesetzt)
    token = st.session_state.get("access_token")
    
    # Priorität 2: Interne Session des Clients (Fallback)
    if not token:
        try:
            session = client.auth.get_session()
            if session:
                token = session.access_token
        except:
            pass

    if token:
        client.postgrest.auth(token)
    
    return client

# --- DATABASE FUNCTIONS ---

def get_user_by_id(user_id):
    """Holt Profildaten für die Authentifizierung."""
    supabase = _get_client()
    try:
        res = supabase.schema("public").table("users").select("is_approved, username").eq("id", user_id).single().execute()
        return res.data
    except Exception as e:
        return None

@st.cache_data(ttl=600)
def get_ref_options(table_name):
    """Fetch reference codes and labels for dropdowns."""
    supabase = _get_client()
    try:
        res = supabase.schema("shared").table(table_name).select("code, label").execute()
        return [f"{item['code']} ({item['label']})" for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Error loading reference data {table_name}: {e}")
        return []

@st.cache_data(ttl=3600)
def get_country_region_map():
    supabase = _get_client()
    res = supabase.schema("shared").table("country_region_mapping").select("country, region_code").execute()
    return {item['country']: item['region_code'] for item in res.data}

def save_asset_static_data(asset_data):
    """Inserts a new asset record."""
    supabase = _get_client()
    return supabase.schema("shared").table("asset_static_data").insert(asset_data).execute()

def update_asset_static_data(isin, updated_data):
    supabase = _get_client()
    try:
        return supabase.schema("shared").table("asset_static_data").update(updated_data).eq("isin", isin).execute()
    except Exception as e:
        st.error(f"Datenbank-Details: {e}")
        raise e

def get_missing_isins(isins: list) -> list:
    if not isins:
        return []
    supabase = _get_client()
    try:
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
    supabase = _get_client()
    flattened_data = []
    try:
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
    supabase = _get_client()
    columns = (
        "user_id, id, account_code, isin, date, transaction_type_code, "
        "quantity, settle_amount, settle_currency, settle_fxrate, amount_eur, "
        "created_at, updated_at, "
        "accounts!fk_accounts(description), "
        "ref_transaction_type!fk_ref_type(label), "
        "asset_static_data!fk_transaction_isin(name)"
    )
    try:
        response = supabase.schema("public").table("transactions").select(columns).eq("user_id", user_id).execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching transactions: {e}")
        return []

def get_asset_ref_options():
    supabase = _get_client()
    try:
        res = supabase.schema("shared").table("asset_static_data").select("isin, name").execute()
        return [f"{item['isin']} ({item['name']})" for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Error loading assets for dropdown: {e}")
        return []

def get_account_ref_options(user_id):
    supabase = _get_client()
    try:
        res = supabase.schema("public").table("accounts").select("account_code, description").eq("user_id", user_id).execute()
        return [f"{item['account_code']} ({item['description']})" for item in res.data] if res.data else []
    except Exception as e:
        st.error(f"Error loading accounts: {e}")
        return []

def get_next_transaction_count(user_id, isin, date_str):
    supabase = _get_client()
    try:
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
    supabase = _get_client()
    try:
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
    supabase = _get_client()
    return supabase.schema("public").table("transactions").insert(transaction_data).execute()

def save_transactions_bulk(payload_list):
    supabase = _get_client()
    try:
        return supabase.schema("public").table("transactions").insert(payload_list).execute()
    except Exception as e:
        print(f"Error during bulk transaction insert: {e}")
        raise e

def get_import_settings(user_id, account_code):
    supabase = _get_client()
    response = supabase.schema("public").table("user_import_settings")\
        .select("mapping_config")\
        .eq("user_id", user_id)\
        .eq("account_code", account_code)\
        .execute()
    return response.data[0]["mapping_config"] if response.data else None

@st.cache_data(ttl=600)
def get_transaction_type_logic():
    supabase = _get_client()
    try:
        res = supabase.schema("shared").table("ref_transaction_logic") \
            .select("transaction_type_code, quantity_sign, amount_sign") \
            .execute()
        if res.data:
            return {
                item['transaction_type_code']: {
                    'quantity_sign': item['quantity_sign'],
                    'amount_sign': item['amount_sign']
                } for item in res.data
            }
        return {}
    except Exception as e:
        st.error(f"Error loading transaction logic: {e}")
        return {}

def save_import_settings(user_id, account_code, config):
    supabase = _get_client()
    payload = {"user_id": user_id, "account_code": account_code, "mapping_config": config}
    supabase.schema("public").table("user_import_settings").upsert(payload).execute()

# --- USER MANAGEMENT FUNCTIONS ---

def get_user_profile(username):
    supabase = _get_client()
    try:
        res = supabase.schema("public").table("users").select("id, username").eq("username", username).execute()
        if res.data:
            data = res.data[0]
            return {"id": data["id"], "username": data["username"]}
        return None
    except Exception as e:
        st.error(f"Error fetching user profile: {e}")
        return None

def get_user_email(user_id):
    supabase = _get_client()
    try:
        res = supabase.schema("public").table("users").select("email").eq("id", user_id).execute()
        return res.data[0].get("email") if res.data else None
    except Exception as e:
        st.error(f"Error fetching user email: {e}")
        return None

def update_user_email(user_id, email):
    supabase = _get_client()
    try:
        supabase.schema("public").table("users").update({"email": email}).eq("id", user_id).execute()
    except Exception as e:
        st.error(f"Error updating email: {e}")
        raise e

def get_user_by_username(username):
    supabase = _get_client()
    try:
        res = supabase.schema("public").table("users").select("id").eq("username", username).execute()
        return res.data[0]["id"] if res.data else None
    except Exception as e:
        st.error(f"Error checking user existence: {e}")
        return None
