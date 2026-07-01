import src.database as database


class ReferencesRepository:
    def get_ref_options(self, table_name: str):
        return database.get_ref_options(table_name)

    def get_account_ref_options(self, user_id: str):
        return database.get_account_ref_options(user_id)

    def get_asset_ref_options(self):
        return database.get_asset_ref_options()

    def get_country_region_map(self):
        return database.get_country_region_map()

    def get_transaction_type_logic(self):
        return database.get_transaction_type_logic()