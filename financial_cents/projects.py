"""Project resource: GET /projects."""

from __future__ import annotations

from typing import Any, Literal

from financial_cents.config import FinancialCentsSettings
from financial_cents.http_client import get_json

ProjectOrderByField = Literal["created_at", "title"]
OrderDirection = Literal["asc", "desc"]
ProjectSearchField = Literal["title"]
SearchOperation = Literal["equals", "beginswith", "endswith", "contains"]
ProjectStatusFilter = Literal["open", "closed", "all"]


def _filter_projects_by_status(
    payload: dict[str, Any], status: ProjectStatusFilter
) -> dict[str, Any]:
    """Keep only open (``is_closed`` false) or closed (``is_closed`` true) projects."""
    if status == "all":
        return payload
    raw = payload.get("data")
    if not isinstance(raw, list):
        return payload
    want_closed = status == "closed"
    filtered = [
        item
        for item in raw
        if isinstance(item, dict) and bool(item.get("is_closed")) is want_closed
    ]
    out = dict(payload)
    out["data"] = filtered
    return out


def list_projects(
    *,
    order_by: ProjectOrderByField | None = "created_at",
    order_dir: OrderDirection | None = "asc",
    page: int | None = 1,
    search_field: ProjectSearchField | None = None,
    search_operation: SearchOperation | None = None,
    search_value: str | None = None,
    status: ProjectStatusFilter | None = "all",
    settings: FinancialCentsSettings | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    List projects (paginated).

    GET https://app.financial-cents.com/api/v1/projects

    Each project includes ``is_closed`` (and typically ``closed_at``, ``closed_by``).
    Search params are only sent when ``search_field``, ``search_operation``, and
    ``search_value`` are all provided.

    When ``status`` is ``open`` or ``closed``, results are filtered client-side to
    that status using ``is_closed``. Pagination ``meta`` still reflects the API
    page; the ``data`` list may be shorter than the page size after filtering.
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

    url = f"{cfg.base_url}/projects"
    payload = get_json(url, params=params, settings=cfg, timeout=timeout)
    effective = status if status is not None else "all"
    return _filter_projects_by_status(payload, effective)
