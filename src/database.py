import logging
from supabase import create_client, Client
import datetime
from datetime import datetime as dt_class

from src.runtime_context import (
    configure_from_env,
    configure_streamlit_context,
    get_current_access_token,
    get_current_user_id,
    get_supabase_config,
    set_context,
    ttl_cache_data,
)


logger = logging.getLogger(__name__)


def initialize_runtime_from_streamlit(st_module) -> None:
    configure_streamlit_context(st_module)


def initialize_runtime_from_env(strict: bool = True) -> bool:
    return configure_from_env(strict=strict)


def set_request_context(access_token=None, user_id=None) -> None:
    set_context(access_token=access_token, user_id=user_id)


def _report_error(message: str, error: Exception) -> None:
    logger.error("%s: %s", message, error)

# --- CLIENT INITIALIZATION ---

def get_admin_client() -> Client:
    """Admin client for bypass RLS (Service Role) - Zentral für interne Zwecke."""
    cfg = get_supabase_config()
    return create_client(cfg.url, cfg.service_key)

def _get_client() -> Client:
    token = get_current_access_token()
    if not token:
        # No user session (headless/nightbatch context): fall back to service role.
        # anon role is fully revoked, so a tokenless anon client would fail anyway.
        return get_admin_client()
    cfg = get_supabase_config()
    client = create_client(cfg.url, cfg.anon_key)
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
        _report_error("Fehler beim Laden der User", e)
        return []

def db_update_user_approval(user_id, status: bool):
    """Schaltet einen User frei oder sperrt ihn (Admin-Funktion)."""
    admin_supabase = get_admin_client()
    return admin_supabase.table("users").update({"is_approved": status}).eq("id", user_id).execute()








# --- DATABASE FUNCTIONS (Assets, Transactions, etc.) ---

@ttl_cache_data(ttl=600)
def get_ref_options(table_name):
    supabase = _get_client()
    try:
        res = supabase.schema("shared").table(table_name).select("code, label").execute()
        return [f"{item['code']} ({item['label']})" for item in res.data] if res.data else []
    except Exception as e:
        _report_error(f"Error loading reference data {table_name}", e)
        return []


@ttl_cache_data(ttl=600)
def get_ref_metadata(table_name):
    """Return reference rows including optional chart metadata like color and display order."""
    supabase = _get_client()
    try:
        res = (
            supabase.schema("shared")
            .table(table_name)
            .select("code, label, color_hex, display_order")
            .execute()
        )
        return res.data if res.data else []
    except Exception as e:
        _report_error(f"Error loading reference metadata {table_name}", e)
        return []

@ttl_cache_data(ttl=3600)
def get_country_region_map():
    supabase = _get_client()
    res = supabase.schema("shared").table("country_region_mapping").select("country, region_code").execute()
    return {item['country']: item['region_code'] for item in res.data}

def get_asset_prices():
    supabase = _get_client()
    try:
        res = (supabase.schema("shared").table("asset_prices")
               .select("isin, price_date, price_close, dividend_cash, split_factor, asset_static_data!fk_prices_isin(name, price_currency)")
               .order("isin")
               .order("price_date", desc=True)
               .execute())
        return res.data if res.data else []
    except Exception as e:
        _report_error("Error loading asset prices", e)
        return []

def get_fx_rates():
    supabase = _get_client()
    try:
        res = (supabase.schema("shared").table("exchange_rates")
               .select("currency, rate_date, exchange_rate, rate_date_original, created_at, updated_at")
               .order("currency")
               .order("rate_date", desc=True)
               .execute())
        return res.data if res.data else []
    except Exception as e:
        _report_error("Error loading FX rates", e)
        return []

def get_non_eur_asset_currency_start_dates():
    """
    Returns the earliest price_start_date for every non-EUR asset currency,
    considering BOTH risk_currency and price_currency.
    """    
    supabase = _get_client()
    try:
        # 1. Fetch both currency columns and the start date
        res = (supabase.schema("shared").table("asset_static_data")
               .select("risk_currency, price_currency, price_start_date")
               .execute())
        
        if not res.data:
            return {}

        currency_dates = {}
        
        # 2. Process every asset row
        for item in res.data:
            start_date = item.get("price_start_date")
            if not start_date:
                continue
            
            # Extract both currencies per asset
            r_curr = item.get("risk_currency")
            p_curr = item.get("price_currency")
            
            # Helper to check and aggregate a currency
            for curr in [r_curr, p_curr]:
                if curr and curr.upper() != "EUR":
                    curr_upper = curr.upper()
                    # Keep the earliest date found for this currency
                    if curr_upper not in currency_dates or start_date < currency_dates[curr_upper]:
                        currency_dates[curr_upper] = start_date

        return currency_dates
        
    except Exception as e:
        _report_error("Error loading asset currency start dates", e)
        return {}


def get_fx_rate_bounds():
    supabase = _get_client()
    try:
        # Wir lesen die View aus
        response = supabase.schema("shared").table("v_exchange_rate_bounds").select("*").execute()
        
        if not response.data:
            return {}

        # Hier nutzen wir das Modul 'datetime' und daraus die Klasse 'date'
        return {
            item['currency']: {
                'min': datetime.date.fromisoformat(item['min_date']),
                'max': datetime.date.fromisoformat(item['max_date'])
            }
            for item in response.data
        }
    except Exception as e:
        # Falls die View noch nicht existiert oder leer ist
        print(f"Fehler in get_fx_rate_bounds: {e}")
        return {}


def get_asset_price_bounds():
    supabase = _get_client()
    try:
        response = supabase.schema("shared").table("v_asset_price_bounds").select("*").execute()

        if not response.data:
            return {}

        return {
            item['isin']: {
                'min': datetime.date.fromisoformat(item['min_date']) if item.get('min_date') else None,
                'max': datetime.date.fromisoformat(item['max_date']) if item.get('max_date') else None,
            }
            for item in response.data
            if item.get('isin')
        }
    except Exception as e:
        print(f"Fehler in get_asset_price_bounds: {e}")
        return {}


def get_fx_rates_for_currency_dates(currencies, min_date=None, max_date=None):
    supabase = _get_client()
    try:
        query = supabase.schema("shared").table("exchange_rates").select(
            "currency, rate_date, exchange_rate, rate_date_original"
        )
        if currencies:
            query = query.in_("currency", currencies)
        if min_date:
            query = query.gte("rate_date", min_date.isoformat())
        if max_date:
            query = query.lte("rate_date", max_date.isoformat())
        res = query.execute()
        return res.data if res.data else []
    except Exception as e:
        print(f"Error loading FX rate records: {e}")
        return []


def save_fx_rates_bulk(payload_list):
    """Upserts FX rate records into the exchange_rates table."""
    if not payload_list:
        return None

    supabase = get_admin_client()
    try:
        # Hinweis: Supabase upsert nutzt den Primary Key (currency, rate_date)
        # Um Duplikate zu vermeiden und Werte zu aktualisieren.
        return supabase.schema("shared").table("exchange_rates").upsert(
            payload_list, 
            on_conflict="currency, rate_date"
        ).execute()
    except Exception as e:
        _report_error("Error saving FX rates", e)
        raise e


def get_asset_price_start_date(isin):
    supabase = _get_client()
    try:
        res = supabase.schema("shared").table("asset_static_data").select("price_start_date").eq("isin", isin).single().execute()
        return res.data.get("price_start_date") if res.data else None
    except Exception as e:
        _report_error("Error loading asset start date", e)
        return None


def get_daily_holdings(user_id=None, holding_date=None, account_codes=None, isins=None):
    """Return daily holdings rows for a user on a specific holding_date."""
    if not user_id:
        user_id = get_current_user_id()
    if not user_id or holding_date is None:
        return []

    if isinstance(holding_date, datetime.date):
        holding_date_str = holding_date.isoformat()
    else:
        holding_date_str = str(holding_date)

    supabase = _get_client()
    try:
        query = (
            supabase.schema("public")
            .table("daily_holdings")
            .select("*")
            .eq("user_id", user_id)
            .eq("holding_date", holding_date_str)
        )

        if account_codes:
            query = query.in_("account_code", account_codes)
        if isins:
            query = query.in_("isin", isins)

        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        _report_error("Error loading daily holdings", e)
        return []

def get_asset_price_start_dates(isins):
    if not isins:
        return {}
    supabase = _get_client()
    try:
        res = supabase.schema("shared").table("asset_static_data").select("isin, price_start_date").in_("isin", isins).execute()
        return {item["isin"]: item.get("price_start_date") for item in res.data} if res.data else {}
    except Exception as e:
        _report_error("Error loading asset start dates", e)
        return {}


def get_assets_by_price_source(price_source_code: str):
    """Return list of assets (isin, ticker, price_currency, price_start_date) for a given price_source_code."""
    supabase = _get_client()
    try:
        res = supabase.schema("shared").table("asset_static_data") \
            .select("isin, ticker, price_currency, price_start_date") \
            .eq("price_source_code", price_source_code).execute()
        return res.data if res.data else []
    except Exception as e:
        _report_error("Error loading assets by price source", e)
        return []


def get_asset_prices_for_isin(isin: str, start_date: str = None, end_date: str = None):
    """Return existing price rows for an ISIN within an optional date range."""
    supabase = _get_client()
    try:
        q = supabase.schema("shared").table("asset_prices").select("isin, price_date, price_close, dividend_cash, split_factor, price_date_original")
        q = q.eq("isin", isin)
        if start_date:
            q = q.gte("price_date", start_date)
        if end_date:
            q = q.lte("price_date", end_date)
        res = q.execute()
        return res.data if res.data else []
    except Exception as e:
        _report_error(f"Error loading asset prices for {isin}", e)
        return []


def save_asset_prices_bulk(payload_list):
    """Bulk upsert asset_prices rows using admin client."""
    if not payload_list:
        return None
    supabase = get_admin_client()
    try:
        return supabase.schema("shared").table("asset_prices").upsert(payload_list, on_conflict="isin, price_date").execute()
    except Exception as e:
        _report_error("Error saving asset prices", e)
        raise e

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
    now = dt_class.now().isoformat()
    user_id = get_current_user_id()
    
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
            _report_error(f"Error updating {item['isin']}", e)
            raise e
    
    return results

def save_asset_static_data(asset_data):
    supabase = get_admin_client()
    return supabase.schema("shared").table("asset_static_data").insert(asset_data).execute()

def update_asset_static_data(isin, updated_data):
    supabase = get_admin_client()
    if "updated_at" not in updated_data:
        updated_data["updated_at"] = dt_class.now().isoformat()
    if "updated_by" not in updated_data:
        user_id = get_current_user_id()
        if user_id:
            updated_data["updated_by"] = user_id
    try:
        return supabase.schema("shared").table("asset_static_data").update(updated_data).eq("isin", isin).execute()
    except Exception as e:
        _report_error("Datenbank-Details", e)
        raise e

def get_missing_isins(isins: list) -> list:
    if not isins: return []
    supabase = _get_client()
    try:
        res = supabase.schema("shared").table("asset_static_data").select("isin").in_("isin", isins).execute()
        existing_isins = {item['isin'] for item in res.data}
        return [i for i in isins if i not in existing_isins]
    except: return []

def get_all_assets_with_labels(isins=None):
    supabase = _get_client()
    flattened_data = []
    try:
        columns = ("isin, name, risk_currency, price_currency, ticker, price_start_date, industry, country, ref_price_source(label), "
                   "ref_instrument_type(label), ref_asset_class(label), ref_region(label), "
                   "ref_sector(label), closed_on, created_at, created_by:users!fk_static_created_by(username), "
                   "updated_by:users!fk_static_updated_by(username), updated_at")
        query = supabase.schema("shared").table("asset_static_data").select(columns)
        if isins:
            query = query.in_("isin", isins)
        query = query.execute()
        if query.data:
            for row in query.data:
                flattened_data.append({
                    "ISIN": row.get("isin"), "Name": row.get("name"), "Ticker": row.get("ticker"),
                    "Risk Currency": row.get("risk_currency"), "Type": (row.get("ref_instrument_type") or {}).get("label"),
                    "Asset Class": (row.get("ref_asset_class") or {}).get("label"),
                    "Region": (row.get("ref_region") or {}).get("label"),
                    "Sector": (row.get("ref_sector") or {}).get("label"), "Industry": row.get("industry"),
                    "Country": row.get("country"), 
                    "Price Source": (row.get("ref_price_source") or {}).get("label"),
                    "Price Currency": row.get("price_currency"),
                    "Price Start Date": row.get("price_start_date"),
                    "Closed On": row.get("closed_on"), "Created At": row.get("created_at"),
                    "Created By": (row.get("created_by") or {}).get("username"),
                    "Updated At": row.get("updated_at"), "Updated By": (row.get("updated_by") or {}).get("username")
                })
    except Exception as e:
        _report_error("Error", e)
    return flattened_data

def get_all_transactions():
    user_id = get_current_user_id()
    if not user_id: return []
    supabase = _get_client()
    columns = ("user_id, id, account_code, isin, date, transaction_type_code, quantity, settle_amount, "
               "settle_currency, settle_fxrate, amount_eur, accounts!fk_accounts(description), "
               "ref_transaction_type!fk_ref_type(label), asset_static_data!fk_transaction_isin(name)")
    try:
        response = supabase.schema("public").table("transactions").select(columns).eq("user_id", user_id).execute()
        return response.data
    except Exception as e:
        _report_error("Error", e)
        return []


def _parse_supabase_timestamp(value):
    if value is None:
        return None
    if isinstance(value, dt_class):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return dt_class.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def get_user_holdings_reorganization_status(user_id=None):
    """Return the latest transaction modification and reorganization timestamps for one user."""
    if not user_id:
        user_id = get_current_user_id()
    if not user_id:
        return None

    supabase = _get_client()
    try:
        response = (
            supabase.schema("public")
            .table("v_user_account_reorganization")
            .select("user_id, account_code, last_transaction_modification, last_reorganization")
            .eq("user_id", user_id)
            .execute()
        )
 
        rows = response.data or []
        if not rows:
            return None

        latest_transaction = None
        latest_reorganization = None

        for row in rows:
            transaction_ts = _parse_supabase_timestamp(row.get("last_transaction_modification"))
            reorganization_ts = _parse_supabase_timestamp(row.get("last_reorganization"))

            if transaction_ts and (latest_transaction is None or transaction_ts > latest_transaction):
                latest_transaction = transaction_ts
            if reorganization_ts and (latest_reorganization is None or reorganization_ts > latest_reorganization):
                latest_reorganization = reorganization_ts



        return {
            "user_id": user_id,
            "last_transaction_modification": latest_transaction,
            "last_reorganization": latest_reorganization,
            "account_count": len(rows),
        }
    except Exception as e:
        _report_error("Error loading user holdings reorganization status", e)
        return None


def get_user_holdings_min_date(user_id=None):
    """Return the earliest available holding_date for one user as a date object."""
    if not user_id:
        user_id = get_current_user_id()
    if not user_id:
        return None

    supabase = _get_client()
    try:
        response = (
            supabase.schema("public")
            .table("incremental_holdings")
            .select("holding_date")
            .eq("user_id", user_id)
            .order("holding_date", desc=False)
            .limit(1)
            .execute()
        )

        rows = response.data or []
        if not rows:
            return None

        value = rows[0].get("holding_date")
        if value is None:
            return None
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, str):
            try:
                return dt_class.fromisoformat(value).date()
            except ValueError:
                return None
        return None
    except Exception as e:
        _report_error("Error loading user holdings min date", e)
        return None


def insert_user_holdings_reorganization(user_id=None):
    """Insert a reorganization marker row for a user."""
    if not user_id:
        user_id = get_current_user_id()
    if not user_id:
        raise ValueError("Missing user_id for holdings reorganization insert")

    supabase = _get_client()
    payload = {"user_id": user_id}
    try:
        return supabase.schema("public").table("user_holdings_reorganization").insert(payload).execute()
    except Exception as e:
        _report_error("Error inserting user holdings reorganization", e)
        raise e


def reorganize_incremental_holdings(user_id=None, account_codes=None, dry_run=False):
    """Run hybrid holdings reorganization via SQL RPC and return summary counters."""
    if not user_id:
        user_id = get_current_user_id()
    if not user_id:
        raise ValueError("Missing user_id for holdings reorganization")

    supabase = _get_client()
    payload = {
        "p_user_id": user_id,
        "p_account_codes": account_codes,
        "p_dry_run": dry_run,
    }

    try:
        response = supabase.rpc("reorganize_incremental_holdings", payload).execute()
        result = response.data

        if result is None:
            return {
                "user_id": user_id,
                "relevant_accounts_count": 0,
                "transactions_scanned": 0,
                "snapshots_generated": 0,
                "rows_deleted": 0,
                "rows_inserted": 0,
                "rows_updated": 0,
                "rows_unchanged": 0,
                "reorg_timestamp_written": False,
                "dry_run": dry_run,
            }

        if isinstance(result, list):
            result = result[0] if result else {}

        if not isinstance(result, dict):
            raise ValueError(f"Unexpected reorganize_incremental_holdings response type: {type(result)}")

        normalized = {
            "user_id": result.get("user_id", user_id),
            "relevant_accounts_count": int(result.get("relevant_accounts_count") or 0),
            "transactions_scanned": int(result.get("transactions_scanned") or 0),
            "snapshots_generated": int(result.get("snapshots_generated") or 0),
            "rows_deleted": int(result.get("rows_deleted") or 0),
            "rows_inserted": int(result.get("rows_inserted") or 0),
            "rows_updated": int(result.get("rows_updated") or 0),
            "rows_unchanged": int(result.get("rows_unchanged") or 0),
            "reorg_timestamp_written": bool(result.get("reorg_timestamp_written", False)),
            "reorg_timestamp": _parse_supabase_timestamp(result.get("reorg_timestamp")),
            "dry_run": bool(result.get("dry_run", dry_run)),
        }
        return normalized
    except Exception as e:
        _report_error("Error running holdings reorganization", e)
        raise e

def get_asset_ref_options():
    supabase = _get_client()
    try:
        res = supabase.schema("shared").table("asset_static_data").select("isin, name").execute()
        return [f"{item['isin']} ({item['name']})" for item in res.data] if res.data else []
    except: return []


def search_exchange_tickers(isin: str = None, name: str = None, active_only: bool = True):
    """Search the shared.exchange_tickers master table by ISIN and/or partial Name."""
    if not isin and not name:
        return []

    supabase = _get_client()
    try:
        query = supabase.schema("shared").table("exchange_tickers").select(
            "ticker_code, exchange_code, price_source_code, name, country, currency, type, isin, ref_exchange(name)"
        )

        if active_only:
            query = query.is_("is_active", True)

        search_isin = isin.strip() if isin else None
        search_name = name.strip() if name else None

        if search_isin and search_name:
            query = query.or_(f"isin.ilike.{search_isin},name.ilike.*{search_name}*")
        elif search_isin:
            query = query.ilike("isin", search_isin)
        elif search_name:
            query = query.ilike("name", f"%{search_name}%")

        response = query.limit(200).order("name", desc=False).execute()
        return response.data if response.data else []
    except Exception as e:
        _report_error("Error searching exchange tickers", e)
        return []

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

@ttl_cache_data(ttl=600)
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
        _report_error("Error loading accounts", e)
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

def delete_all_transactions(user_id):
    """Deletes all transactions and holdings for the given user_id."""
    supabase = _get_client()
    supabase.schema("public").table("transactions").delete().eq("user_id", user_id).execute()
    return supabase.schema("public").table("incremental_holdings").delete().eq("user_id", user_id).execute()
