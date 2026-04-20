"""Time activities resource: GET /time-activities."""

from __future__ import annotations

from typing import Any

from financial_cents.config import FinancialCentsSettings
from financial_cents.http_client import get_json


def list_time_activities(
    *,
    date_range_start: str | None = None,
    date_range_end: str | None = None,
    client_id: int | None = None,
    user_id: int | None = None,
    settings: FinancialCentsSettings | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    List time activities with optional filters.

    GET https://app.financial-cents.com/api/v1/time-activities

    ``date_range_start`` / ``date_range_end`` must be ``YYYY-MM-DD`` when set.
    They map to query keys ``date_range[start]`` and ``date_range[end]``.

    Typical fields in each ``data`` item: ``id``, ``date``, ``hours``, ``comments``,
    and a nested ``user`` object (``id``, ``name``).
    """
    cfg = settings or FinancialCentsSettings.from_env()
    params: dict[str, Any] = {}
    if date_range_start is not None:
        params["date_range[start]"] = date_range_start
    if date_range_end is not None:
        params["date_range[end]"] = date_range_end
    if client_id is not None:
        params["client_id"] = client_id
    if user_id is not None:
        params["user_id"] = user_id

    url = f"{cfg.base_url}/time-activities"
    return get_json(url, params=params, settings=cfg, timeout=timeout)
