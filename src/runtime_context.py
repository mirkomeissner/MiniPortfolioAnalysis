import os
import time
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
from threading import RLock
from typing import Any, Callable, Dict, Optional, Tuple


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    service_key: str
    anon_key: str


_config: Optional[SupabaseConfig] = None
_context_provider: Optional[Callable[[], Dict[str, Optional[str]]]] = None
_request_context: ContextVar[Optional[Dict[str, Optional[str]]]] = ContextVar("request_context", default=None)


def _validate_config(url: Optional[str], service_key: Optional[str], anon_key: Optional[str]) -> SupabaseConfig:
    if not url or not service_key or not anon_key:
        raise RuntimeError(
            "Supabase config is incomplete. Expected SUPABASE_URL, SUPABASE_SERVICE_KEY and SUPABASE_KEY."
        )
    return SupabaseConfig(url=url, service_key=service_key, anon_key=anon_key)


def configure_supabase(url: str, service_key: str, anon_key: str) -> None:
    global _config
    _config = _validate_config(url, service_key, anon_key)


def configure_from_env(strict: bool = True) -> bool:
    url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    anon_key = os.environ.get("SUPABASE_KEY")

    if not (url and service_key and anon_key):
        if strict:
            _validate_config(url, service_key, anon_key)
        return False

    configure_supabase(url, service_key, anon_key)
    return True


def configure_streamlit_context(st_module: Any) -> None:
    configure_supabase(
        st_module.secrets["SUPABASE_URL"],
        st_module.secrets["SUPABASE_SERVICE_KEY"],
        st_module.secrets["SUPABASE_KEY"],
    )

    set_context_provider(
        lambda: {
            "access_token": st_module.session_state.get("access_token"),
            "user_id": st_module.session_state.get("user_id"),
        }
    )


def set_context_provider(provider: Optional[Callable[[], Dict[str, Optional[str]]]]) -> None:
    global _context_provider
    _context_provider = provider


def set_context(access_token: Optional[str] = None, user_id: Optional[str] = None) -> None:
    _request_context.set({"access_token": access_token, "user_id": user_id})


def clear_context() -> None:
    _request_context.set(None)


def _get_context() -> Dict[str, Optional[str]]:
    request_context = _request_context.get()
    if request_context is not None:
        return request_context
    if _context_provider is None:
        return {"access_token": None, "user_id": None}
    try:
        return _context_provider() or {"access_token": None, "user_id": None}
    except Exception:
        return {"access_token": None, "user_id": None}


def get_current_access_token() -> Optional[str]:
    return _get_context().get("access_token")


def get_current_user_id() -> Optional[str]:
    return _get_context().get("user_id")


def get_supabase_config() -> SupabaseConfig:
    if _config is None:
        configured = configure_from_env(strict=False)
        if not configured:
            raise RuntimeError(
                "Supabase config not initialized. "
                "Call configure_streamlit_context(st) in UI mode or configure_from_env() in headless mode."
            )
    return _config


def ttl_cache_data(ttl: int = 600) -> Callable:
    """Framework-agnostic cache decorator with a simple per-process TTL."""

    def decorator(func: Callable) -> Callable:
        cache: Dict[Tuple[Any, ...], Tuple[Any, float]] = {}
        lock = RLock()

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            with lock:
                if key in cache:
                    value, ts = cache[key]
                    if now - ts < ttl:
                        return value

            value = func(*args, **kwargs)
            with lock:
                cache[key] = (value, now)
            return value

        def clear():
            with lock:
                cache.clear()

        wrapper.clear = clear
        return wrapper

    return decorator
