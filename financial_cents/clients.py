"""Client resource: GET /clients, GET /clients/{client_id}, POST /clients."""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import quote

from financial_cents.config import FinancialCentsSettings
from financial_cents.http_client import get_json, post_form_json

OrderByField = Literal["created_at", "updated_at", "name"]
OrderDirection = Literal["asc", "desc"]
SearchField = Literal["name"]
SearchOperation = Literal["equals", "beginswith", "endswith", "contains"]


def _client_url(base_url: str, client_id: str | int) -> str:
    # Path segment must be encoded if IDs ever contain reserved chars
    cid = quote(str(client_id), safe="")
    return f"{base_url}/clients/{cid}"


def get_client(
    client_id: str | int,
    *,
    settings: FinancialCentsSettings | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    Fetch a single client by ID.

    GET https://app.financial-cents.com/api/v1/clients/{client_id}
    """
    cfg = settings or FinancialCentsSettings.from_env()
    url = _client_url(cfg.base_url, client_id)
    return get_json(url, settings=cfg, timeout=timeout)


def list_clients(
    *,
    order_by: OrderByField | None = "name",
    order_dir: OrderDirection | None = "asc",
    page: int | None = 1,
    search_field: SearchField | None = None,
    search_operation: SearchOperation | None = None,
    search_value: str | None = None,
    settings: FinancialCentsSettings | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    List clients (paginated).

    GET https://app.financial-cents.com/api/v1/clients

    Search params are only sent when ``search_field``, ``search_operation``, and
    ``search_value`` are all provided.
    """
    cfg = settings or FinancialCentsSettings.from_env()
    params: dict[str, Any] = {}
    if order_by is not None:
        params["order_by"] = order_by
    if order_dir is not None:
        params["order_dir"] = order_dir
    if page is not None:
        params["page"] = page
    if (
        search_field is not None
        and search_operation is not None
        and search_value is not None
    ):
        params["search[field]"] = search_field
        params["search[operation]"] = search_operation
        params["search[value]"] = search_value

    url = f"{cfg.base_url}/clients"
    return get_json(url, params=params, settings=cfg, timeout=timeout)


def create_client(
    *,
    display_name: str,
    contact_name: str | None = None,
    contact_email: str | None = None,
    contact_address: str | None = None,
    contact_notes: str | None = None,
    settings: FinancialCentsSettings | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    Create a client.

    POST https://app.financial-cents.com/api/v1/clients

    Body: form fields
    - display_name (required)
    - contact_name, contact_email, contact_address, contact_notes (optional)
    """
    name = (display_name or "").strip()
    if not name:
        raise ValueError("display_name is required.")

    cfg = settings or FinancialCentsSettings.from_env()
    url = f"{cfg.base_url}/clients"
    return post_form_json(
        url,
        form={
            "display_name": name,
            "contact_name": (contact_name or "").strip() or None,
            "contact_email": (contact_email or "").strip() or None,
            "contact_address": (contact_address or "").strip() or None,
            "contact_notes": (contact_notes or "").strip() or None,
        },
        settings=cfg,
        timeout=timeout,
    )
