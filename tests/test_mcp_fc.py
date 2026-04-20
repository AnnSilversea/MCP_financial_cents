"""Unit tests for MCP tool wrappers (mocked API)."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from financial_cents.config import FinancialCentsSettings

from mcp_fc import server as mcp_server


class TestMcpTools(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = FinancialCentsSettings(
            base_url="https://app.financial-cents.com/api/v1",
            api_token="test-token",
        )

    @patch.object(mcp_server, "_settings")
    @patch("mcp_fc.server.list_clients")
    def test_check_connection_calls_list_clients(
        self, mock_list: unittest.mock.MagicMock, mock_settings: unittest.mock.MagicMock
    ) -> None:
        mock_settings.return_value = self.settings
        mock_list.return_value = {"data": [], "meta": {"page": 1}}

        out = mcp_server.financial_cents_check_connection()

        mock_list.assert_called_once_with(page=1, settings=self.settings)
        data = json.loads(out)
        self.assertTrue(data["ok"])
        self.assertEqual(data["base_url"], self.settings.base_url)

    @patch.object(mcp_server, "_settings")
    @patch("mcp_fc.server.list_clients")
    def test_list_clients_forwards_params(
        self, mock_list: unittest.mock.MagicMock, mock_settings: unittest.mock.MagicMock
    ) -> None:
        mock_settings.return_value = self.settings
        mock_list.return_value = {"data": []}

        mcp_server.financial_cents_list_clients(
            order_by="name",
            order_dir="desc",
            page=2,
            search_field="name",
            search_operation="contains",
            search_value="Acme",
        )

        mock_list.assert_called_once_with(
            order_by="name",
            order_dir="desc",
            page=2,
            search_field="name",
            search_operation="contains",
            search_value="Acme",
            settings=self.settings,
        )

    @patch.object(mcp_server, "_settings")
    @patch("mcp_fc.server.get_client")
    def test_get_client_forwards_id(
        self, mock_get: unittest.mock.MagicMock, mock_settings: unittest.mock.MagicMock
    ) -> None:
        mock_settings.return_value = self.settings
        mock_get.return_value = {"id": 1}

        mcp_server.financial_cents_get_client(1670387)

        mock_get.assert_called_once_with(1670387, settings=self.settings)

    @patch.object(mcp_server, "_settings")
    @patch("mcp_fc.server.list_projects")
    def test_list_projects_forwards_params(
        self, mock_lp: unittest.mock.MagicMock, mock_settings: unittest.mock.MagicMock
    ) -> None:
        mock_settings.return_value = self.settings
        mock_lp.return_value = {"data": []}

        mcp_server.financial_cents_list_projects(page=3)

        mock_lp.assert_called_once_with(
            order_by="created_at",
            order_dir="asc",
            page=3,
            search_field=None,
            search_operation=None,
            search_value=None,
            status="all",
            settings=self.settings,
        )

    @patch.object(mcp_server, "_settings")
    @patch("mcp_fc.server.list_project_resources")
    def test_list_project_resources_forwards_params(
        self,
        mock_lpr: unittest.mock.MagicMock,
        mock_settings: unittest.mock.MagicMock,
    ) -> None:
        mock_settings.return_value = self.settings
        mock_lpr.return_value = {"data": []}

        mcp_server.financial_cents_list_project_resources(
            project_id=8017,
            order_by="label",
            order_dir="desc",
            search_field="label",
            search_operation="contains",
            search_value="tax",
        )

        mock_lpr.assert_called_once_with(
            8017,
            order_by="label",
            order_dir="desc",
            search_field="label",
            search_operation="contains",
            search_value="tax",
            settings=self.settings,
        )

    @patch.object(mcp_server, "_settings")
    @patch("mcp_fc.server.list_client_resources")
    def test_list_client_resources_forwards_params(
        self,
        mock_lcr: unittest.mock.MagicMock,
        mock_settings: unittest.mock.MagicMock,
    ) -> None:
        mock_settings.return_value = self.settings
        mock_lcr.return_value = {"data": []}

        mcp_server.financial_cents_list_client_resources(
            client_id=7956,
            order_by="label",
            order_dir="desc",
            search_field="label",
            search_operation="contains",
            search_value="bookkeeping",
        )

        mock_lcr.assert_called_once_with(
            7956,
            order_by="label",
            order_dir="desc",
            search_field="label",
            search_operation="contains",
            search_value="bookkeeping",
            settings=self.settings,
        )

    @patch.object(mcp_server, "_settings")
    def test_missing_token_returns_configuration_error(
        self, mock_settings: unittest.mock.MagicMock
    ) -> None:
        mock_settings.side_effect = ValueError("Missing API token")

        out = mcp_server.financial_cents_check_connection()
        data = json.loads(out)
        self.assertEqual(data["error"], "configuration_error")
        self.assertIn("Missing API token", data["detail"])

    @patch.object(mcp_server, "_settings")
    @patch("mcp_fc.server.list_time_activities")
    def test_list_time_activities_forwards_params(
        self, mock_lt: unittest.mock.MagicMock, mock_settings: unittest.mock.MagicMock
    ) -> None:
        mock_settings.return_value = self.settings
        mock_lt.return_value = {"data": []}

        mcp_server.financial_cents_list_time_activities(
            date_range_start="2024-07-01",
            date_range_end="2024-07-31",
            client_id=1,
            user_id=2,
        )

        mock_lt.assert_called_once_with(
            date_range_start="2024-07-01",
            date_range_end="2024-07-31",
            client_id=1,
            user_id=2,
            settings=self.settings,
        )

    @patch.object(mcp_server, "_settings")
    @patch("mcp_fc.server.list_client_tasks")
    def test_list_client_tasks_forwards_params(
        self, mock_lct: unittest.mock.MagicMock, mock_settings: unittest.mock.MagicMock
    ) -> None:
        mock_settings.return_value = self.settings
        mock_lct.return_value = {"data": []}

        mcp_server.financial_cents_list_client_tasks(
            project_status="closed",
            is_completed=True,
            limit=25,
            search_field="title",
            search_operation="contains",
            search_value="tax",
        )

        mock_lct.assert_called_once_with(
            order_by="due_date",
            order_dir="asc",
            page=1,
            project_status="closed",
            is_completed=True,
            limit=25,
            search_field="title",
            search_operation="contains",
            search_value="tax",
            settings=self.settings,
        )


if __name__ == "__main__":
    unittest.main()
