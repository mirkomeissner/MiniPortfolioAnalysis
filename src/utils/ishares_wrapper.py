import os
import time
from datetime import date

import requests

from .mock_data_utils import generate_ishares_excel_bytes, is_unknown_ticker, raise_provider_not_found


ISHARE_URL_TEMPLATE = (
    "https://www.ishares.com/de/privatanleger/de/produkte/{ticker}/fund/1535604580385.ajax"
    "?fileType=xls&dataType=fund"
)


class MyIsharesProxy:
    @property
    def is_dev(self) -> bool:
        return os.getenv("APP_ENV", "main").lower() == "dev"

    def fetch_excel_bytes(self, ticker: str, currency: str, retries: int = 3, timeout: int = 15) -> bytes:
        if self.is_dev:
            if is_unknown_ticker(ticker):
                raise_provider_not_found("ishares", ticker)
            return generate_ishares_excel_bytes(
                ticker=ticker,
                start="2025-01-01",
                end=date.today(),
                currency=(currency or "USD").upper(),
            )

        url = ISHARE_URL_TEMPLATE.format(ticker=ticker)
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(url, timeout=timeout)
                resp.raise_for_status()
                return resp.content
            except Exception as exc:
                last_exc = exc
                time.sleep(1 * attempt)

        raise last_exc


my_ishares = MyIsharesProxy()
