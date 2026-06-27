import os
from datetime import date

import requests

from .mock_data_utils import generate_eod_rows, is_unknown_ticker, raise_provider_not_found


EODHD_URL_TEMPLATE = "https://eodhd.com/api/eod/{ticker}"


class MyEODHDProxy:
    @property
    def is_dev(self) -> bool:
        return os.getenv("APP_ENV", "main").lower() == "dev"

    def fetch_history(self, ticker: str, api_key: str, request_start_date: date, timeout: int = 15):
        if self.is_dev:
            if is_unknown_ticker(ticker):
                raise_provider_not_found("eodhd", ticker)
            return generate_eod_rows(ticker=ticker, start=request_start_date, end=date.today())

        params = {
            "api_token": api_key,
            "fmt": "json",
            "from": request_start_date.isoformat(),
        }
        response = requests.get(EODHD_URL_TEMPLATE.format(ticker=ticker), params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []


my_eodhd = MyEODHDProxy()
