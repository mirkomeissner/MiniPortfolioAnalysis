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
        """Simuliert die history() Methode für Volumen-Berechnungen."""
        import pandas as pd
        import numpy as np
        dates = pd.date_range(end=pd.Timestamp.now(), periods=14)
        return pd.DataFrame({
            "Volume": np.random.randint(100000, 1000000, size=14)
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

