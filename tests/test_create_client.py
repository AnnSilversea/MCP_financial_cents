"""Unit tests for create_client (mocked HTTP)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from financial_cents.clients import create_client
from financial_cents.config import FinancialCentsSettings


class TestCreateClient(unittest.TestCase):
    def test_create_client_posts_form_fields(self) -> None:
        settings = FinancialCentsSettings(
            base_url="https://app.financial-cents.com/api/v1",
            api_token="test-token",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 873, "name": "FC LLC"}
        mock_response.raise_for_status = MagicMock()

        with patch("financial_cents.http_client._get_shared_client") as get_shared_client:
            instance = MagicMock()
            get_shared_client.return_value = instance
            instance.post.return_value = mock_response

            out = create_client(
                display_name="FC LLC",
                contact_name="John Doe",
                contact_email="test@example.com",
                contact_address="123 Main St, Knoxville, TN 37922",
                contact_notes="any notes related to this contact",
                settings=settings,
            )

        instance.post.assert_called_once()
        url = instance.post.call_args[0][0]
        self.assertEqual(url, "https://app.financial-cents.com/api/v1/clients")
        headers = instance.post.call_args[1]["headers"]
        self.assertEqual(headers["Authorization"], "Bearer test-token")
        self.assertEqual(headers["Accept"], "application/json")
        data = instance.post.call_args[1]["data"]
        self.assertEqual(
            data,
            {
                "display_name": "FC LLC",
                "contact_name": "John Doe",
                "contact_email": "test@example.com",
                "contact_address": "123 Main St, Knoxville, TN 37922",
                "contact_notes": "any notes related to this contact",
            },
        )
        self.assertEqual(out["id"], 873)

    def test_create_client_omits_empty_optional_fields(self) -> None:
        settings = FinancialCentsSettings(
            base_url="https://app.financial-cents.com/api/v1",
            api_token="test-token",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1}
        mock_response.raise_for_status = MagicMock()

        with patch("financial_cents.http_client._get_shared_client") as get_shared_client:
            instance = MagicMock()
            get_shared_client.return_value = instance
            instance.post.return_value = mock_response

            create_client(
                display_name="  ACME  ",
                contact_name="",
                contact_email=None,
                settings=settings,
            )

        data = instance.post.call_args[1]["data"]
        self.assertEqual(data, {"display_name": "ACME"})


if __name__ == "__main__":
    unittest.main()

