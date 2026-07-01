import src.database as database


class AuthRepository:
    def get_user_profile(self, user_id: str):
        return database.db_get_user_profile(user_id)

    def approve_user(self, user_id: str):
        return database.db_approve_user(user_id)

    def login(self, email: str, password: str):
        return database.auth_login(email, password)

    def register(self, email: str, password: str, username: str):
        return database.auth_register(email, password, username)

    def logout(self):
        return database.auth_logout()

    def update_user(self, data: dict):
        return database.auth_update_user(data)

    def check_existing_email(self, email: str) -> bool:
        return database.check_existing_email(email)