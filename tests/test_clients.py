"""Unit tests for get_client (mocked HTTP)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from financial_cents.clients import get_client, list_clients
from financial_cents.config import FinancialCentsSettings


class TestGetClient(unittest.TestCase):
    def test_get_client_builds_url_and_returns_json(self) -> None:
        settings = FinancialCentsSettings(
            base_url="https://app.financial-cents.com/api/v1",
            api_token="test-token",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 7956, "name": "Example"}
        mock_response.raise_for_status = MagicMock()

        with patch("financial_cents.http_client._get_shared_client") as get_shared_client:
            instance = MagicMock()
            get_shared_client.return_value = instance
            instance.get.return_value = mock_response

            result = get_client(7956, settings=settings)

        instance.get.assert_called_once()
        call_kw = instance.get.call_args
        self.assertEqual(
            call_kw[0][0],
            "https://app.financial-cents.com/api/v1/clients/7956",
        )
        headers = call_kw[1]["headers"]
        self.assertEqual(headers["Authorization"], "Bearer test-token")
        self.assertEqual(headers["Accept"], "application/json")
        self.assertEqual(result, {"id": 7956, "name": "Example"})


class TestListClients(unittest.TestCase):
    def test_list_clients_query_string(self) -> None:
        settings = FinancialCentsSettings(
            base_url="https://app.financial-cents.com/api/v1",
            api_token="test-token",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [], "meta": {"page": 1}}
        mock_response.raise_for_status = MagicMock()

        with patch("financial_cents.http_client._get_shared_client") as get_shared_client:
            instance = MagicMock()
            get_shared_client.return_value = instance
            instance.get.return_value = mock_response

            result = list_clients(
                order_by="name",
                order_dir="asc",
                page=1,
                search_field="name",
                search_operation="contains",
                search_value="Acme",
                settings=settings,
            )

        instance.get.assert_called_once()
        call_kw = instance.get.call_args
        self.assertEqual(call_kw[0][0], "https://app.financial-cents.com/api/v1/clients")
        self.assertEqual(
            call_kw[1]["params"],
            {
                "order_by": "name",
                "order_dir": "asc",
                "page": 1,
                "search[field]": "name",
                "search[operation]": "contains",
                "search[value]": "Acme",
            },
        )
        self.assertEqual(result, {"data": [], "meta": {"page": 1}})

    def test_list_clients_omits_search_if_incomplete(self) -> None:
        settings = FinancialCentsSettings(
            base_url="https://app.financial-cents.com/api/v1",
            api_token="test-token",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        with patch("financial_cents.http_client._get_shared_client") as get_shared_client:
            instance = MagicMock()
            get_shared_client.return_value = instance
            instance.get.return_value = mock_response

            list_clients(search_value="only-value", settings=settings)

        params = instance.get.call_args[1]["params"]
        self.assertNotIn("search[field]", params)
        self.assertNotIn("search[value]", params)


if __name__ == "__main__":
    unittest.main()
