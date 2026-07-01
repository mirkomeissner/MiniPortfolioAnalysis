from src.utils.email_service import send_duplicate_info_mail

from backend.app.repositories.auth_repository import AuthRepository


_DEFAULT_REPOSITORY = AuthRepository()


def _get_attr(obj, name: str, default=None):
    if obj is None:
        return default
    return getattr(obj, name, default)


def _normalize_admin_emails(admin_emails: list[str] | None) -> set[str]:
    return {str(email).strip().lower() for email in (admin_emails or []) if str(email).strip()}


def get_user_profile_record(user_id: str, repository: AuthRepository | None = None) -> dict | None:
    repo = repository or _DEFAULT_REPOSITORY
    profile = repo.get_user_profile(user_id)
    if not profile:
        return None

    return {
        "id": profile.get("id") or user_id,
        "username": profile.get("username"),
        "email": profile.get("email"),
        "is_approved": bool(profile.get("is_approved")),
        "pending_email": profile.get("pending_email"),
    }


def login_user(email: str, password: str, repository: AuthRepository | None = None) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    try:
        response = repo.login(email, password)
    except Exception:
        return {
            "authenticated": False,
            "access_token": None,
            "user_id": None,
            "username": None,
            "email": email,
            "is_approved": False,
            "pending_email": None,
        }

    session = _get_attr(response, "session")
    user = _get_attr(response, "user")
    access_token = _get_attr(session, "access_token")
    user_id = _get_attr(user, "id")
    profile = repo.get_user_profile(user_id) if user_id else None

    return {
        "authenticated": bool(access_token and user_id),
        "access_token": access_token,
        "user_id": user_id,
        "username": profile.get("username") if profile else _get_attr(user, "email"),
        "email": _get_attr(user, "email", email),
        "is_approved": bool(profile and profile.get("is_approved")),
        "pending_email": profile.get("pending_email") if profile else None,
    }


def register_user(
    email: str,
    password: str,
    username: str,
    admin_emails: list[str] | None = None,
    repository: AuthRepository | None = None,
) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    clean_email = email.strip().lower()
    normalized_admin_emails = _normalize_admin_emails(admin_emails)

    try:
        if repo.check_existing_email(clean_email):
            try:
                send_duplicate_info_mail(clean_email)
            except Exception:
                pass
            return {"user_created": True, "duplicate_email": True, "user_id": None}

        response = repo.register(email, password, username)
        user = _get_attr(response, "user")
        user_id = _get_attr(user, "id")
        if user_id and clean_email in normalized_admin_emails:
            repo.approve_user(user_id)

        return {"user_created": bool(user), "duplicate_email": False, "user_id": user_id}
    except Exception as exc:
        error_msg = str(exc).lower()
        if "already registered" in error_msg or "already exists" in error_msg:
            try:
                send_duplicate_info_mail(clean_email)
            except Exception:
                pass
            return {"user_created": True, "duplicate_email": True, "user_id": None}
        raise


def logout_user(repository: AuthRepository | None = None) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    repo.logout()
    return {"logged_out": True}


def update_password(password: str, repository: AuthRepository | None = None) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    repo.update_user({"password": password})
    return {"updated": True}


def update_username(username: str, repository: AuthRepository | None = None) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    repo.update_user({"data": {"username": username}})
    return {"updated": True, "username": username}


def update_email(email: str, repository: AuthRepository | None = None) -> dict:
    repo = repository or _DEFAULT_REPOSITORY
    repo.update_user({"email": email})
    return {"updated": True, "email": email}