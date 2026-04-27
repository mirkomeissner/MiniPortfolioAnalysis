import os
import yfinance as yf

# --- MOCK HILFSKLASSEN ---

class MockTicker:
    """Simuliert ein yfinance Ticker-Objekt."""
    def __init__(self, ticker_symbol):
        self.ticker_symbol = ticker_symbol
        # Hier kannst du beliebige Testdaten hinterlegen
        self.info = {
            "isin": "DE000MOCK01",
            "longName": f"{ticker_symbol} Mock Corp",
            "currency": "EUR",
            "currentPrice": 123.45,
            "navPrice": 123.45,
            "exchange": "FRA",
            "sector": "Technology",
            "country": "Germany",
            "quoteType": "EQUITY",
            "volume": 1000000
        }

    def history(self, *args, **kwargs):
        """Simuliert die history() Methode für historische Kurse."""
        import pandas as pd
        import numpy as np

        start = kwargs.get("start")
        end = kwargs.get("end")
        if start is None:
            start = pd.Timestamp.now() - pd.Timedelta(days=14)
        else:
            start = pd.to_datetime(start)

        if end is None:
            end = pd.Timestamp.now()
        else:
            end = pd.to_datetime(end)

        if start > end:
            start, end = end, start

        dates = pd.date_range(start=start, end=end, freq="D")
        return pd.DataFrame({
            "Close": np.round(np.random.uniform(0.5, 2.0, size=len(dates)), 6),
            "Volume": np.random.randint(100000, 1000000, size=len(dates))
        }, index=dates)

class MockSearch:
    """Simuliert das yf.Search Objekt."""
    def __init__(self, query):
        self.quotes = [
            {"symbol": "AAPL", "longname": "Apple Inc. (Mock)", "quoteType": "EQUITY", "isin": "US0378331005"},
            {"symbol": "SAP.DE", "longname": "SAP SE (Mock)", "quoteType": "EQUITY", "isin": "DE0007164600"},
        ]

# --- DAS PROXY OBJEKT ---

class MyYFinanceProxy:
    """
    Dieser Proxy entscheidet basierend auf APP_ENV, 
    ob echte Daten oder Mocks geliefert werden.
    """
    @property
    def is_dev(self):
        return os.getenv("APP_ENV", "main").lower() == "dev"

    def Search(self, query, **kwargs):
        if self.is_dev:
            return MockSearch(query)
        return yf.Search(query, **kwargs)

    def Ticker(self, ticker_symbol, **kwargs):
        if self.is_dev:
            return MockTicker(ticker_symbol)
        return yf.Ticker(ticker_symbol, **kwargs)

# Instanz erstellen, die du im restlichen Projekt importierst
my_yf = MyYFinanceProxy()

