"""Unit tests for list_project_resources (mocked HTTP)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from financial_cents.config import FinancialCentsSettings
from financial_cents.project_resources import list_project_resources


class TestListProjectResources(unittest.TestCase):
    def test_list_project_resources_minimal_url(self) -> None:
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

            list_project_resources(8017, settings=settings)

        instance.get.assert_called_once()
        self.assertEqual(
            instance.get.call_args[0][0],
            "https://app.financial-cents.com/api/v1/projects/8017/resources",
        )
        self.assertEqual(instance.get.call_args[1]["params"], {})

    def test_list_project_resources_order_and_search(self) -> None:
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

            list_project_resources(
                "417",
                order_by="label",
                order_dir="desc",
                search_field="label",
                search_operation="contains",
                search_value="dashboard",
                settings=settings,
            )

        params = instance.get.call_args[1]["params"]
        self.assertEqual(
            instance.get.call_args[0][0],
            "https://app.financial-cents.com/api/v1/projects/417/resources",
        )
        self.assertEqual(
            params,
            {
                "order_by": "label",
                "order_dir": "desc",
                "search[field]": "label",
                "search[operation]": "contains",
                "search[value]": "dashboard",
            },
        )

    def test_list_project_resources_returns_documented_shape(self) -> None:
        """Example payload from API docs (integration-style assertion on parse)."""
        settings = FinancialCentsSettings(
            base_url="https://app.financial-cents.com/api/v1",
            api_token="test-token",
        )
        sample = {
            "data": [
                {
                    "id": 2578,
                    "project_id": 417,
                    "anchor_id": "6905d188-c511-4804-9787-bf133253bad6",
                    "label": "resource label",
                    "url": "http://fc.test/dashboard/9",
                    "list_index": 1,
                    "type": None,
                    "created_at": "2023-10-24T09:42:44.000000Z",
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

            out = list_project_resources(417, settings=settings)

        self.assertEqual(out, sample)
        row = out["data"][0]
        self.assertEqual(row["id"], 2578)
        self.assertEqual(row["label"], "resource label")
        self.assertIn("anchor_id", row)


if __name__ == "__main__":
    unittest.main()
