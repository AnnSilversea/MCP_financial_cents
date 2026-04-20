"""Unit tests for list_projects (mocked HTTP)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from financial_cents.config import FinancialCentsSettings
from financial_cents.projects import list_projects


class TestListProjects(unittest.TestCase):
    def test_list_projects_default_params(self) -> None:
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

            list_projects(settings=settings)

        instance.get.assert_called_once()
        self.assertEqual(
            instance.get.call_args[0][0],
            "https://app.financial-cents.com/api/v1/projects",
        )
        self.assertEqual(
            instance.get.call_args[1]["params"],
            {
                "order_by": "created_at",
                "order_dir": "asc",
                "page": 1,
            },
        )

    def test_list_projects_with_title_search(self) -> None:
        settings = FinancialCentsSettings(
            base_url="https://app.financial-cents.com/api/v1",
            api_token="test-token",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        with patch("financial_cents.http_client._get_shared_client") as get_client:
            instance = MagicMock()
            get_client.return_value = instance
            instance.get.return_value = mock_response

            list_projects(
                order_by="title",
                search_field="title",
                search_operation="contains",
                search_value="Tax",
                settings=settings,
            )

        params = instance.get.call_args[1]["params"]
        self.assertEqual(params["search[field]"], "title")
        self.assertEqual(params["search[operation]"], "contains")
        self.assertEqual(params["search[value]"], "Tax")

    def test_list_projects_filters_open_status(self) -> None:
        settings = FinancialCentsSettings(
            base_url="https://app.financial-cents.com/api/v1",
            api_token="test-token",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"id": 1, "title": "A", "is_closed": False},
                {"id": 2, "title": "B", "is_closed": True},
            ],
            "meta": {"page": 1},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("financial_cents.http_client._get_shared_client") as get_client:
            instance = MagicMock()
            get_client.return_value = instance
            instance.get.return_value = mock_response

            out = list_projects(status="open", settings=settings)

        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["id"], 1)
        self.assertEqual(out["meta"]["page"], 1)


if __name__ == "__main__":
    unittest.main()
