"""HTTP helpers: authenticated JSON requests."""

from __future__ import annotations

import atexit
import threading
from typing import Any

import httpx

from financial_cents.config import FinancialCentsSettings


_CLIENT_LOCK = threading.Lock()
_CLIENT: httpx.Client | None = None


def _get_shared_client(*, timeout: float) -> httpx.Client:
    """
    Return a shared httpx.Client to keep TCP connections warm.

    Creating a new Client for every request disables connection pooling and can
    make the whole system feel slow (especially under many tool calls).
    """
    global _CLIENT
    with _CLIENT_LOCK:
        if _CLIENT is None or _CLIENT.is_closed:
            # Conservative limits; can be tuned later without changing API.
            limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
            _CLIENT = httpx.Client(timeout=timeout, limits=limits)
        else:
            # Keep timeout aligned with the current call.
            _CLIENT.timeout = timeout
        return _CLIENT


@atexit.register
def _close_shared_client() -> None:
    global _CLIENT
    with _CLIENT_LOCK:
        if _CLIENT is not None and not _CLIENT.is_closed:
            _CLIENT.close()
        _CLIENT = None


def build_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }


def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    settings: FinancialCentsSettings | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Perform GET and parse JSON object response."""
    cfg = settings or FinancialCentsSettings.from_env()
    client = _get_shared_client(timeout=timeout)
    response = client.get(url, headers=build_headers(cfg.api_token), params=params)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        msg = f"Expected JSON object from API, got {type(data).__name__}"
        raise TypeError(msg)
    return data


def post_form_json(
    url: str,
    *,
    form: dict[str, Any] | None = None,
    settings: FinancialCentsSettings | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    Perform POST with form fields and parse JSON object response.

    Financial Cents "Create" endpoints often expect `multipart/form-data` style
    fields; sending `data=` is compatible with that requirement in httpx.
    """
    cfg = settings or FinancialCentsSettings.from_env()
    payload = {k: v for k, v in (form or {}).items() if v is not None}
    client = _get_shared_client(timeout=timeout)
    response = client.post(url, headers=build_headers(cfg.api_token), data=payload)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        msg = f"Expected JSON object from API, got {type(data).__name__}"
        raise TypeError(msg)
    return data
