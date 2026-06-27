import os
from datetime import date

import requests

from .mock_data_utils import generate_tiingo_rows, is_unknown_ticker, raise_provider_not_found


TIINGO_URL_TEMPLATE = "https://api.tiingo.com/tiingo/daily/{ticker}/prices"


class MyTiingoProxy:
    """Proxy for Tiingo that switches between live and deterministic mock data."""

    @property
    def is_dev(self) -> bool:
        return os.getenv("APP_ENV", "main").lower() == "dev"

    def fetch_history(self, ticker_symbol: str, api_key: str, request_start_date: date, timeout: int = 15):
        if self.is_dev:
            if is_unknown_ticker(ticker_symbol):
                raise_provider_not_found("tiingo", ticker_symbol)
            return generate_tiingo_rows(
                ticker=ticker_symbol,
                start=request_start_date,
                end=date.today(),
            )

        params = {
            "startDate": request_start_date.isoformat(),
            "token": api_key,
        }
        response = requests.get(TIINGO_URL_TEMPLATE.format(ticker=ticker_symbol), params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []

    def get_latest_price(self, ticker_symbol):
        if self.is_dev and is_unknown_ticker(ticker_symbol):
            raise_provider_not_found("tiingo", ticker_symbol)

        try:
            rows = self.fetch_history(
                ticker_symbol=ticker_symbol,
                api_key=os.getenv("TIINGO_API_KEY"),
                request_start_date=date.today(),
                timeout=5,
            )
            if rows:
                data = rows[-1]
                return {
                    "price": data.get("close"),
                    "currency": "USD" if not str(ticker_symbol).upper().endswith(".DE") else "EUR",
                }
            return {"price": None, "currency": None}
        except Exception:
            return {"price": None, "currency": None}


my_tiingo = MyTiingoProxy()
