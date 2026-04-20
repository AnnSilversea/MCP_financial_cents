"""Client resources: GET /clients/{client_id}/resources."""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import quote

from financial_cents.config import FinancialCentsSettings
from financial_cents.http_client import get_json

ClientResourceOrderByField = Literal["created_at", "label", "list_index"]
OrderDirection = Literal["asc", "desc"]
ClientResourceSearchField = Literal["label"]
SearchOperation = Literal["equals", "beginswith", "endswith", "contains"]


def _client_resources_url(base_url: str, client_id: str | int) -> str:
    cid = quote(str(client_id), safe="")
    return f"{base_url}/clients/{cid}/resources"


def list_client_resources(
    client_id: str | int,
    *,
    order_by: ClientResourceOrderByField | None = None,
    order_dir: OrderDirection | None = None,
    search_field: ClientResourceSearchField | None = None,
    search_operation: SearchOperation | None = None,
    search_value: str | None = None,
    settings: FinancialCentsSettings | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    List links/resources attached to a client.

    GET https://app.financial-cents.com/api/v1/clients/{client_id}/resources

    Response shape is typically ``{"data": [ {...}, ... ]}`` where each item may
    include ``id``, ``client_id``, ``label``, ``url``, ``list_index``, ``type``,
    ``created_at``, ``updated_at``.

    Search params are only sent when ``search_field``, ``search_operation``,
    and ``search_value`` are all provided.
    """
    cfg = settings or FinancialCentsSettings.from_env()
    params: dict[str, Any] = {}
    if order_by is not None:
        params["order_by"] = order_by
    if order_dir is not None:
        params["order_dir"] = order_dir
    if (
        search_field is not None
        and search_operation is not None
        and search_value is not None
    ):
        params["search[field]"] = search_field
        params["search[operation]"] = search_operation
        params["search[value]"] = search_value

    url = _client_resources_url(cfg.base_url, client_id)
    return get_json(url, params=params, settings=cfg, timeout=timeout)
