"""Project resources: GET /projects/{project_id}/resources."""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import quote

from financial_cents.config import FinancialCentsSettings
from financial_cents.http_client import get_json

ProjectResourceOrderByField = Literal["created_at", "label", "list_index"]
OrderDirection = Literal["asc", "desc"]
ProjectResourceSearchField = Literal["label"]
SearchOperation = Literal["equals", "beginswith", "endswith", "contains"]


def _project_resources_url(base_url: str, project_id: str | int) -> str:
    pid = quote(str(project_id), safe="")
    return f"{base_url}/projects/{pid}/resources"


def list_project_resources(
    project_id: str | int,
    *,
    order_by: ProjectResourceOrderByField | None = None,
    order_dir: OrderDirection | None = None,
    search_field: ProjectResourceSearchField | None = None,
    search_operation: SearchOperation | None = None,
    search_value: str | None = None,
    settings: FinancialCentsSettings | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    List links/resources attached to a project.

    GET https://app.financial-cents.com/api/v1/projects/{project_id}/resources

    Response shape is typically ``{"data": [ {...}, ... ]}`` where each item may
    include ``id``, ``project_id``, ``anchor_id``, ``label``, ``url``,
    ``list_index``, ``type``, ``created_at``.

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

    url = _project_resources_url(cfg.base_url, project_id)
    return get_json(url, params=params, settings=cfg, timeout=timeout)
