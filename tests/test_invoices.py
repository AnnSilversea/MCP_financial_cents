"""Unit tests for list_invoices (mocked HTTP)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from financial_cents.config import FinancialCentsSettings
from financial_cents.invoices import list_invoices


class TestListInvoices(unittest.TestCase):
    def test_list_invoices_default_params(self) -> None:
        settings = FinancialCentsSettings(
            base_url="https://app.financial-cents.com/api/v1",
            api_token="test-token",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch("financial_cents.http_client._get_shared_client") as get_client:
            instance = MagicMock()
            get_client.return_value = instance
            instance.get.return_value = mock_response

            list_invoices(settings=settings)

        instance.get.assert_called_once()
        self.assertEqual(
            instance.get.call_args[0][0],
            "https://app.financial-cents.com/api/v1/invoices",
        )
        self.assertEqual(
            instance.get.call_args[1]["params"],
            {"order_by": "due_date", "order_dir": "asc", "page": 1},
        )

    def test_list_invoices_custom_order(self) -> None:
        settings = FinancialCentsSettings(
            base_url="https://app.financial-cents.com/api/v1",
            api_token="test-token",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch("financial_cents.http_client._get_shared_client") as get_client:
            instance = MagicMock()
            get_client.return_value = instance
            instance.get.return_value = mock_response

            list_invoices(order_by="amount_due", order_dir="desc", page=3, settings=settings)

        params = instance.get.call_args[1]["params"]
        self.assertEqual(params["order_by"], "amount_due")
        self.assertEqual(params["order_dir"], "desc")
        self.assertEqual(params["page"], 3)


if __name__ == "__main__":
    unittest.main()

