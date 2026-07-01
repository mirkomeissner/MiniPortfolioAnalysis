import src.database as database


class TransactionsRepository:
    def get_all_transactions_for_user(self, user_id):
        return database.get_all_transactions_for_user(user_id)

    def save_transaction(self, transaction_data):
        return database.save_transaction(transaction_data)

    def save_transactions_bulk(self, transaction_list):
        return database.save_transactions_bulk(transaction_list)

    def get_import_settings(self, user_id: str, account_code: str):
        return database.get_import_settings(user_id, account_code)

    def save_import_settings(self, user_id: str, account_code: str, mapping_config: dict):
        return database.save_import_settings(user_id, account_code, mapping_config)

    def delete_all_transactions_for_user(self, user_id: str):
        return database.delete_all_transactions(user_id)

    def get_existing_ids_for_bulk(self, user_id: str, isins: list[str], dates: list[str]):
        return database.get_existing_ids_for_bulk(user_id, isins, dates)

    def get_missing_isins(self, isins: list[str]):
        return database.get_missing_isins(isins)

    def get_next_transaction_count(self, user_id: str, isin: str, date_str: str):
        return database.get_next_transaction_count(user_id, isin, date_str)