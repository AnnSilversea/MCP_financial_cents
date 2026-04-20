"""Unit tests for list_client_tasks (mocked HTTP)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from financial_cents.config import FinancialCentsSettings
from financial_cents.client_tasks import list_client_tasks


class TestListClientTasks(unittest.TestCase):
    def test_list_client_tasks_default_params(self) -> None:
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

            list_client_tasks(settings=settings)

        instance.get.assert_called_once()
        self.assertEqual(
            instance.get.call_args[0][0],
            "https://app.financial-cents.com/api/v1/client-tasks",
        )
        self.assertEqual(
            instance.get.call_args[1]["params"],
            {
                "order_by": "due_date",
                "order_dir": "asc",
                "page": 1,
                "project_status": "all",
            },
        )

    def test_list_client_tasks_project_status_and_optional(self) -> None:
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

            list_client_tasks(
                project_status="open",
                is_completed=False,
                limit=50,
                settings=settings,
            )

        params = instance.get.call_args[1]["params"]
        self.assertEqual(params["project_status"], "open")
        self.assertIs(params["is_completed"], False)
        self.assertEqual(params["limit"], 50)

    def test_list_client_tasks_search(self) -> None:
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

            list_client_tasks(
                search_field="client_name",
                search_operation="contains",
                search_value="ocea",
                settings=settings,
            )

        params = instance.get.call_args[1]["params"]
        self.assertEqual(params["search[field]"], "client_name")
        self.assertEqual(params["search[operation]"], "contains")
        self.assertEqual(params["search[value]"], "ocea")


if __name__ == "__main__":
    unittest.main()
