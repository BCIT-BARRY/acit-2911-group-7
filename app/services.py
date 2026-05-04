from __future__ import annotations

from dataclasses import dataclass

import requests


@dataclass(slots=True)
class FinnhubSnapshot:
    symbol: str
    company_name: str
    current_price: float | None
    previous_close: float | None
    open_price: float | None
    high_price: float | None
    low_price: float | None
    change: float | None
    percent_change: float | None
    last_updated: str | None


class FinnhubClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def get_profile(self, symbol: str) -> dict:
        response = requests.get(
            "https://finnhub.io/api/v1/stock/profile2",
            params={"symbol": symbol, "token": self.api_key},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_quote(self, symbol: str) -> dict:
        response = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": symbol, "token": self.api_key},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def build_snapshot(self, symbol: str) -> FinnhubSnapshot:
        normalized_symbol = symbol.upper().strip()

        profile_data: dict = {}
        quote_data: dict = {}

        try:
            profile_data = self.get_profile(normalized_symbol)
        except requests.RequestException:
            profile_data = {}

        try:
            quote_data = self.get_quote(normalized_symbol)
        except requests.RequestException:
            quote_data = {}

        current_price = quote_data.get("c")
        previous_close = quote_data.get("pc")
        open_price = quote_data.get("o")
        high_price = quote_data.get("h")
        low_price = quote_data.get("l")
        change = quote_data.get("d")
        percent_change = quote_data.get("dp")

        company_name = profile_data.get("name") or normalized_symbol

        return FinnhubSnapshot(
            symbol=normalized_symbol,
            company_name=company_name,
            current_price=current_price,
            previous_close=previous_close,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            change=change,
            percent_change=percent_change,
            last_updated=quote_data.get("t") and str(quote_data.get("t")),
        )