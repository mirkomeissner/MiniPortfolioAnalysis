import src.database as database


class HoldingsRepository:
    def get_user_holdings_min_date(self, user_id=None):
        return database.get_user_holdings_min_date(user_id)

    def get_daily_holdings(self, user_id=None, holding_date=None, account_codes=None, isins=None):
        return database.get_daily_holdings(
            user_id=user_id,
            holding_date=holding_date,
            account_codes=account_codes,
            isins=isins,
        )

    def get_all_assets_with_labels(self, isins=None):
        return database.get_all_assets_with_labels(isins)

    def get_ref_metadata(self, table_name):
        return database.get_ref_metadata(table_name)

    def get_user_holdings_reorganization_status(self, user_id: str):
        return database.get_user_holdings_reorganization_status(user_id)

    def reorganize_incremental_holdings(self, user_id: str, account_codes=None, dry_run: bool = False):
        return database.reorganize_incremental_holdings(
            user_id=user_id,
            account_codes=account_codes,
            dry_run=dry_run,
        )