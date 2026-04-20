"""Unit tests for list_time_activities (mocked HTTP)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from financial_cents.config import FinancialCentsSettings
from financial_cents.time_activities import list_time_activities


class TestListTimeActivities(unittest.TestCase):
    def test_list_time_activities_no_optional_params(self) -> None:
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

            list_time_activities(settings=settings)

        instance.get.assert_called_once()
        self.assertEqual(
            instance.get.call_args[0][0],
            "https://app.financial-cents.com/api/v1/time-activities",
        )
        self.assertEqual(instance.get.call_args[1]["params"], {})

    def test_list_time_activities_forwards_filters(self) -> None:
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

            list_time_activities(
                date_range_start="2024-07-01",
                date_range_end="2024-07-31",
                client_id=42,
                user_id=28,
                settings=settings,
            )

        params = instance.get.call_args[1]["params"]
        self.assertEqual(params["date_range[start]"], "2024-07-01")
        self.assertEqual(params["date_range[end]"], "2024-07-31")
        self.assertEqual(params["client_id"], 42)
        self.assertEqual(params["user_id"], 28)


if __name__ == "__main__":
    unittest.main()
