import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# --- CLIENT INITIALIZATION ---

def get_admin_client() -> Client:
    """Admin client for bypass RLS (Service Role) - Zentral für interne Zwecke."""
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_KEY"])

def _get_client() -> Client:
    client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    
    # Wir verlassen uns NUR auf unseren Session State
    token = st.session_state.get("access_token")
    
    if token:
        client.postgrest.auth(token)
        client.auth.set_session(token, "any-refresh-token")
    
    return client

# --- AUTH & USER DB OPERATIONS ---

def db_get_user_profile(user_id):
    """Holt Profildaten für Authentifizierung und Einstellungen."""
    supabase = _get_client()
    try:
        res = supabase.schema("public").table("users").select("*").eq("id", user_id).single().execute()
        return res.data
    except:
        return None

def db_approve_user(user_id):
    """Setzt is_approved auf True (erfordert Admin/Service Role)."""
    admin_supabase = get_admin_client()
    return admin_supabase.table("users").update({"is_approved": True}).eq("id", user_id).execute()



# --- AUTH ACTIONS ---

def auth_login(email, password):
    """Führt den Login aus und gibt die Response zurück."""
    supabase = _get_client()
    return supabase.auth.sign_in_with_password({"email": email, "password": password})

def auth_register(email, password, username):
    """Registriert einen neuen User."""
    supabase = _get_client()
    return supabase.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": {"username": username}}
    })

def auth_logout():
    """Meldet den User bei Supabase ab."""
    supabase = _get_client()
    return supabase.auth.sign_out()

def auth_update_user(data):
    """Aktualisiert User-Daten wie Passwort oder Email."""
    supabase = _get_client()
    return supabase.auth.update_user(data)

def check_existing_email(email: str) -> bool:
    """
    Prüft in der public.users Tabelle, ob eine E-Mail bereits existiert.
    Nutzt den Admin-Client, um RLS zu umgehen.
    """
    admin_supabase = get_admin_client()
    try:
        # Wir suchen nach der E-Mail und lassen uns nur die ID zurückgeben
        res = admin_supabase.table("users") \
            .select("id") \
            .eq("email", email) \
            .execute()
        
        # Wenn Daten zurückkommen, existiert die E-Mail
        return len(res.data) > 0
    except Exception as e:
        # Im Fehlerfall (z.B. Verbindungsprobleme) loggen wir es
        print(f"Fehler bei check_existing_email: {e}")
        return False




# --- ADMIN DB OPERATIONS ---

def db_get_all_users():
    """Holt alle User mit bestätigter Email (Admin-Funktion)."""
    admin_supabase = get_admin_client()
    try:
        response = admin_supabase.table("users").select("*")\
            .not_.is_("email_confirmed_at", "null")\
            .order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Fehler beim Laden der User: {e}")
        return []

def db_update_user_approval(user_id, status: bool):
    """Schaltet einen User frei oder sperrt ihn (Admin-Funktion)."""
    admin_supabase = get_admin_client()
    return admin_supabase.table("users").update({"is_approved": status}).eq("id", user_id).execute()








# --- DATABASE FUNCTIONS (Assets, Transactions, etc.) ---

@st.cache_data(ttl=600)
def get_ref_options(table_name):
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

def get_asset_prices():
    supabase = _get_client()
    try:
        res = (supabase.schema("shared").table("asset_prices")
               .select("isin, price_date, price_close, asset_static_data!fk_prices_isin(name)")
               .order("isin")
               .order("price_date", desc=True)
               .execute())
        return res.data if res.data else []
    except Exception as e:
        st.error(f"Error loading asset prices: {e}")
        return []

def get_fx_rates():
    supabase = _get_client()
    try:
        res = (supabase.schema("shared").table("exchange_rates")
               .select("currency, rate_date, exchange_rate")
               .order("currency")
               .order("rate_date", desc=True)
               .execute())
        return res.data if res.data else []
    except Exception as e:
        st.error(f"Error loading FX rates: {e}")
        return []

def get_asset_price_start_date(isin):
    supabase = _get_client()
    try:
        res = supabase.schema("shared").table("asset_static_data").select("price_start_date").eq("isin", isin).single().execute()
        return res.data.get("price_start_date") if res.data else None
    except Exception as e:
        st.error(f"Error loading asset start date: {e}")
        return None

def get_asset_price_start_dates(isins):
    if not isins:
        return {}
    supabase = _get_client()
    try:
        res = supabase.schema("shared").table("asset_static_data").select("isin, price_start_date").in_("isin", isins).execute()
        return {item["isin"]: item.get("price_start_date") for item in res.data} if res.data else {}
    except Exception as e:
        st.error(f"Error loading asset start dates: {e}")
        return {}

def update_asset_start_date(isin, start_date):
    return update_asset_static_data(isin, {"price_start_date": start_date})

def update_asset_start_dates_bulk(payload_list):
    """
    Bulk update price_start_date for multiple existing ISINs.
    
    Uses individual update requests since partial bulk updates require custom SQL logic.
    The calling code ensures assets exist before this helper is called.
    """
    if not payload_list:
        return None
    
    supabase = get_admin_client()
    now = datetime.now().isoformat()
    user_id = st.session_state.get("user_id")
    
    results = []
    for item in payload_list:
        try:
            update_data = {
                "price_start_date": item["price_start_date"],
                "updated_at": now,
            }
            if user_id:
                update_data["updated_by"] = user_id
            
            result = supabase.schema("shared").table("asset_static_data").update(update_data).eq("isin", item["isin"]).execute()
            results.append(result)
        except Exception as e:
            st.error(f"Error updating {item['isin']}: {e}")
            raise e
    
    return results

def save_asset_static_data(asset_data):
    supabase = _get_client()
    return supabase.schema("shared").table("asset_static_data").insert(asset_data).execute()

def update_asset_static_data(isin, updated_data):
    supabase = _get_client()
    if "updated_at" not in updated_data:
        updated_data["updated_at"] = datetime.now().isoformat()
    if "updated_by" not in updated_data:
        user_id = st.session_state.get("user_id")
        if user_id:
            updated_data["updated_by"] = user_id
    try:
        return supabase.schema("shared").table("asset_static_data").update(updated_data).eq("isin", isin).execute()
    except Exception as e:
        st.error(f"Datenbank-Details: {e}")
        raise e

def get_missing_isins(isins: list) -> list:
    if not isins: return []
    supabase = _get_client()
    try:
        res = supabase.schema("shared").table("asset_static_data").select("isin").in_("isin", isins).execute()
        existing_isins = {item['isin'] for item in res.data}
        return [i for i in isins if i not in existing_isins]
    except: return []

def get_all_assets_with_labels():
    supabase = _get_client()
    flattened_data = []
    try:
        columns = ("isin, name, currency, ticker, price_start_date, industry, country, ref_price_source(label), "
                   "ref_instrument_type(label), ref_asset_class(label), ref_region(label), "
                   "ref_sector(label), closed_on, created_at, created_by:users!fk_static_created_by(username), "
                   "updated_by:users!fk_static_updated_by(username), updated_at")
        query = supabase.schema("shared").table("asset_static_data").select(columns).execute()
        if query.data:
            for row in query.data:
                flattened_data.append({
                    "ISIN": row.get("isin"), "Name": row.get("name"), "Ticker": row.get("ticker"),
                    "Currency": row.get("currency"), "Type": (row.get("ref_instrument_type") or {}).get("label"),
                    "Asset Class": (row.get("ref_asset_class") or {}).get("label"),
                    "Region": (row.get("ref_region") or {}).get("label"),
                    "Sector": (row.get("ref_sector") or {}).get("label"), "Industry": row.get("industry"),
                    "Country": row.get("country"), "Price Source": (row.get("ref_price_source") or {}).get("label"),
                    "Price Start Date": row.get("price_start_date"), "Closed On": row.get("closed_on"), "Created At": row.get("created_at"),
                    "Created By": (row.get("created_by") or {}).get("username"),
                    "Updated At": row.get("updated_at"), "Updated By": (row.get("updated_by") or {}).get("username")
                })
    except Exception as e: st.error(f"Error: {e}")
    return flattened_data

def get_all_transactions():
    user_id = st.session_state.get('user_id')
    if not user_id: return []
    supabase = _get_client()
    columns = ("user_id, id, account_code, isin, date, transaction_type_code, quantity, settle_amount, "
               "settle_currency, settle_fxrate, amount_eur, accounts!fk_accounts(description), "
               "ref_transaction_type!fk_ref_type(label), asset_static_data!fk_transaction_isin(name)")
    try:
        response = supabase.schema("public").table("transactions").select(columns).eq("user_id", user_id).execute()
        return response.data
    except Exception as e: st.error(f"Error: {e}"); return []

def get_asset_ref_options():
    supabase = _get_client()
    try:
        res = supabase.schema("shared").table("asset_static_data").select("isin, name").execute()
        return [f"{item['isin']} ({item['name']})" for item in res.data] if res.data else []
    except: return []

def get_account_ref_options(user_id):
    supabase = _get_client()
    try:
        res = supabase.schema("public").table("accounts").select("account_code, description").eq("user_id", user_id).execute()
        return [f"{item['account_code']} ({item['description']})" for item in res.data] if res.data else []
    except: return []

def get_next_transaction_count(user_id, isin, date_str):
    supabase = _get_client()
    try:
        res = supabase.schema("public").table("transactions").select("id").eq("user_id", user_id).eq("isin", isin).eq("date", date_str).execute()
        return len(res.data) + 1
    except: return 1

def get_existing_ids_for_bulk(user_id, isins, dates):
    supabase = _get_client()
    try:
        response = supabase.schema("public").table("transactions").select("id").eq("user_id", user_id).in_("isin", isins).in_("date", dates).execute()
        return [item['id'] for item in response.data]
    except: return []

def save_transaction(transaction_data):
    supabase = _get_client()
    return supabase.schema("public").table("transactions").insert(transaction_data).execute()

def save_transactions_bulk(payload_list):
    supabase = _get_client()
    try: return supabase.schema("public").table("transactions").insert(payload_list).execute()
    except Exception as e: raise e

def get_import_settings(user_id, account_code):
    supabase = _get_client()
    response = supabase.schema("public").table("user_import_settings").select("mapping_config").eq("user_id", user_id).eq("account_code", account_code).execute()
    return response.data[0]["mapping_config"] if response.data else None

@st.cache_data(ttl=600)
def get_transaction_type_logic():
    supabase = _get_client()
    try:
        res = supabase.schema("shared").table("ref_transaction_logic").select("transaction_type_code, quantity_sign, amount_sign").execute()
        return {i['transaction_type_code']: {'quantity_sign': i['quantity_sign'], 'amount_sign': i['amount_sign']} for i in res.data} if res.data else {}
    except: return {}

def save_import_settings(user_id, account_code, config):
    supabase = _get_client()
    payload = {"user_id": user_id, "account_code": account_code, "mapping_config": config}
    supabase.schema("public").table("user_import_settings").upsert(payload).execute()

# --- ACCOUNT MANAGEMENT FUNCTIONS ---

def get_all_accounts(user_id):
    supabase = _get_client()
    try:
        res = supabase.schema("public").table("accounts").select("account_code, description").eq("user_id", user_id).execute()
        return res.data
    except Exception as e:
        st.error(f"Error loading accounts: {e}")
        return []

def save_account(user_id, account_code, description):
    supabase = _get_client()
    payload = {"user_id": user_id, "account_code": account_code, "description": description}
    return supabase.schema("public").table("accounts").insert(payload).execute()

def update_account(user_id, account_code, description):
    supabase = _get_client()
    return supabase.schema("public").table("accounts").update({"description": description}).eq("user_id", user_id).eq("account_code", account_code).execute()

def delete_account(user_id, account_code):
    supabase = _get_client()
    return supabase.schema("public").table("accounts").delete().eq("user_id", user_id).eq("account_code", account_code).execute()
