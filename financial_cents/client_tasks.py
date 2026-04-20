"""Client tasks resource: GET /client-tasks."""

from __future__ import annotations

from typing import Any, Literal

from financial_cents.clients import OrderDirection, SearchOperation
from financial_cents.config import FinancialCentsSettings
from financial_cents.http_client import get_json
from financial_cents.projects import ProjectStatusFilter

ClientTaskOrderByField = Literal["due_date"]
ClientTaskSearchField = Literal["title", "client_name"]


def list_client_tasks(
    *,
    order_by: ClientTaskOrderByField | None = "due_date",
    order_dir: OrderDirection | None = "asc",
    page: int | None = 1,
    project_status: ProjectStatusFilter | None = "all",
    is_completed: bool | None = None,
    limit: int | None = None,
    search_field: ClientTaskSearchField | None = None,
    search_operation: SearchOperation | None = None,
    search_value: str | None = None,
    settings: FinancialCentsSettings | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    List client tasks (paginated).

    GET https://app.financial-cents.com/api/v1/client-tasks

    ``project_status`` filters by parent project: ``open``, ``closed``, or ``all``.

    ``limit`` is typically between 10 and 200 when set (API default applies when omitted).

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
    if project_status is not None:
        params["project_status"] = project_status
    if is_completed is not None:
        params["is_completed"] = is_completed
    if limit is not None:
        params["limit"] = limit
    if (
        search_field is not None
        and search_operation is not None
        and search_value is not None
    ):
        params["search[field]"] = search_field
        params["search[operation]"] = search_operation
        params["search[value]"] = search_value

    url = f"{cfg.base_url}/client-tasks"
    return get_json(url, params=params, settings=cfg, timeout=timeout)
