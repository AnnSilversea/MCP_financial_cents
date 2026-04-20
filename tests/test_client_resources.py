"""Unit tests for list_client_resources (mocked HTTP)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from financial_cents.config import FinancialCentsSettings
from financial_cents.client_resources import list_client_resources


class TestListClientResources(unittest.TestCase):
    def test_list_client_resources_minimal_url(self) -> None:
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

            list_client_resources(7956, settings=settings)

        instance.get.assert_called_once()
        self.assertEqual(
            instance.get.call_args[0][0],
            "https://app.financial-cents.com/api/v1/clients/7956/resources",
        )
        self.assertEqual(instance.get.call_args[1]["params"], {})

    def test_list_client_resources_order_and_search(self) -> None:
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

            list_client_resources(
                1,
                order_by="label",
                order_dir="desc",
                search_field="label",
                search_operation="contains",
                search_value="bookkeeping",
                settings=settings,
            )

        params = instance.get.call_args[1]["params"]
        self.assertEqual(
            instance.get.call_args[0][0],
            "https://app.financial-cents.com/api/v1/clients/1/resources",
        )
        self.assertEqual(
            params,
            {
                "order_by": "label",
                "order_dir": "desc",
                "search[field]": "label",
                "search[operation]": "contains",
                "search[value]": "bookkeeping",
            },
        )

    def test_list_client_resources_returns_documented_shape(self) -> None:
        settings = FinancialCentsSettings(
            base_url="https://app.financial-cents.com/api/v1",
            api_token="test-token",
        )
        sample = {
            "data": [
                {
                    "id": 1,
                    "client_id": 1,
                    "label": "monthly bookkeeping",
                    "url": "http://fc.test/resource/9",
                    "list_index": 0,
                    "created_at": "2023-10-24T09:42:44.000000Z",
                    "updated_at": "2023-10-25T09:42:44.000000Z",
                }
            ]
        }
        mock_response = MagicMock()
        mock_response.json.return_value = sample
        mock_response.raise_for_status = MagicMock()

        with patch("financial_cents.http_client._get_shared_client") as get_client:
            instance = MagicMock()
            get_client.return_value = instance
            instance.get.return_value = mock_response

            out = list_client_resources(7956, settings=settings)

        self.assertEqual(out, sample)
        row = out["data"][0]
        self.assertEqual(row["label"], "monthly bookkeeping")


if __name__ == "__main__":
    unittest.main()
