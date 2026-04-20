"""Invoices resource: GET /invoices."""

from __future__ import annotations

from typing import Any, Literal

from financial_cents.clients import OrderDirection
from financial_cents.config import FinancialCentsSettings
from financial_cents.http_client import get_json

InvoiceOrderByField = Literal[
    "created_at",
    "updated_at",
    "invoice_date",
    "due_date",
    "amount_due",
]


def list_invoices(
    *,
    order_by: InvoiceOrderByField | None = "due_date",
    order_dir: OrderDirection | None = "asc",
    page: int | None = 1,
    settings: FinancialCentsSettings | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    List invoices (paginated).

    GET https://app.financial-cents.com/api/v1/invoices

    Common query params:
    - order_by: one of created_at, updated_at, invoice_date, due_date, amount_due
    - order_dir: asc/desc
    - page: integer page number
    """
    cfg = settings or FinancialCentsSettings.from_env()
    params: dict[str, Any] = {}
    if order_by is not None:
        params["order_by"] = order_by
    if order_dir is not None:
        params["order_dir"] = order_dir
    if page is not None:
        params["page"] = page

    url = f"{cfg.base_url}/invoices"
    return get_json(url, params=params, settings=cfg, timeout=timeout)

