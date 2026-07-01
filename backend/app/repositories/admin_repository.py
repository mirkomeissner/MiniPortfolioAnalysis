import src.database as database


class AdminRepository:
    def get_all_users(self):
        return database.db_get_all_users()

    def update_user_approval(self, user_id: str, is_approved: bool):
        return database.db_update_user_approval(user_id, is_approved)