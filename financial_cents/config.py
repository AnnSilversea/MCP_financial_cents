"""Load API settings from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = "https://app.financial-cents.com/api/v1"


@dataclass(frozen=True)
class FinancialCentsSettings:
    """Credentials and base URL for the Financial Cents API."""

    base_url: str
    api_token: str

    @classmethod
    def from_env(cls) -> FinancialCentsSettings:
        token = (os.getenv("FINANCIAL_CENTS_API_TOKEN") or "").strip()
        if not token:
            msg = (
                "Missing API token. Set FINANCIAL_CENTS_API_TOKEN in the "
                "environment or .env file."
            )
            raise ValueError(msg)
        base = os.getenv("FINANCIAL_CENTS_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        return cls(base_url=base, api_token=token)
