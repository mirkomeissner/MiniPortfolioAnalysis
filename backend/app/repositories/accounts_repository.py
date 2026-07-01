import src.database as database


class AccountsRepository:
    def get_all_accounts(self, user_id):
        return database.get_all_accounts(user_id)

    def save_account(self, user_id, account_code, description):
        return database.save_account(user_id, account_code, description)

    def update_account(self, user_id, account_code, description):
        return database.update_account(user_id, account_code, description)

    def delete_account(self, user_id, account_code):
        return database.delete_account(user_id, account_code)