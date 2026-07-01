from backend.app.repositories.references_repository import ReferencesRepository


_DEFAULT_REPOSITORY = ReferencesRepository()


def get_reference_bootstrap(user_id: str, repository: ReferencesRepository | None = None) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    return {
        "opt_asset": repo.get_ref_options("ref_asset_class"),
        "opt_gics": repo.get_ref_options("ref_sector"),
        "opt_region": repo.get_ref_options("ref_region"),
        "opt_type": repo.get_ref_options("ref_instrument_type"),
        "opt_source": repo.get_ref_options("ref_price_source"),
        "opt_trans_types": repo.get_ref_options("ref_transaction_type"),
        "opt_accounts": repo.get_account_ref_options(user_id),
        "opt_assets": repo.get_asset_ref_options(),
        "db_region_map": repo.get_country_region_map(),
        "type_logic_map": repo.get_transaction_type_logic(),
    }