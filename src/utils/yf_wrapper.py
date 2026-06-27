import os
import pandas as pd
import yfinance as yf

from .mock_data_utils import (
    COMMON_EUR_FX_RATES,
    generate_mock_ohlcv,
    is_unknown_ticker,
    raise_provider_not_found,
)

# --- FIXED MOCK FX DATA (NO WEEKENDS, DETERMINISTIC) ---

def _get_mock_fx_data(symbol, start, end):
    """
    Returns deterministic FX mock data for testing.
    Supports 20+ common EUR pairs plus arbitrary FX symbols.
    Weekdays only (Mon-Fri), no random drops.
    """
    return generate_mock_ohlcv(symbol, start=start, end=end, include_holiday_gaps=False)

def _generate_mock_data(start, end):
    """
    Helper to create synthetic price dataframes with deterministic market gaps.
    Simulates missing data for weekends (standard) and deterministic holidays.
    """
    return generate_mock_ohlcv("GENERIC", start=start, end=end, include_holiday_gaps=True)

# --- MOCK CLASSES ---

class MockTicker:
    """Simulates a yfinance Ticker object."""
    def __init__(self, ticker_symbol):
        self.ticker_symbol = ticker_symbol
        self.info = {
            "isin": "DE000MOCK01",
            "longName": f"{ticker_symbol} Mock Corp",
            "currency": "EUR",
            "currentPrice": 1.12,
            "quoteType": "CURRENCY" if "=X" in ticker_symbol else "EQUITY",
            "exchange": "CCY" if "=X" in ticker_symbol else "FRA",
        }

    def history(self, *args, **kwargs):
        """Simulates the history() method for a single ticker."""
        if is_unknown_ticker(self.ticker_symbol):
            raise_provider_not_found("yfinance", self.ticker_symbol)
        return _generate_mock_data(kwargs.get("start"), kwargs.get("end"))

class MockSearch:
    """Simulates the yf.Search object."""
    def __init__(self, query):
        query_text = str(query or "").strip()
        if is_unknown_ticker(query_text):
            self.quotes = []
            return

        self.quotes = [
            {"symbol": "AAPL", "longname": "Apple Inc. (Mock)", "quoteType": "EQUITY", "isin": "US0378331005"},
            {"symbol": "SAP.DE", "longname": "SAP SE (Mock)", "quoteType": "EQUITY", "isin": "DE0007164600"},
            {"symbol": "EURUSD=X", "longname": "EUR/USD (Mock)", "quoteType": "CURRENCY", "isin": None},
        ]

# --- THE PROXY OBJECT ---

class MyYFinanceProxy:
    """
    This Proxy decides based on APP_ENV whether to deliver 
    live data from yfinance or local mock data.
    """

    COMMON_FX_SYMBOLS = sorted(COMMON_EUR_FX_RATES.keys())
    
    @property
    def is_dev(self) -> bool:
        """Checks if the application is running in development mode."""
        return os.getenv("APP_ENV", "main").lower() == "dev"

    def Search(self, query, **kwargs):
        """Proxy for yf.Search."""
        if self.is_dev:
            return MockSearch(query)
        return yf.Search(query, **kwargs)

    def Ticker(self, ticker_symbol, **kwargs):
        """Proxy for yf.Ticker."""
        if self.is_dev:
            if is_unknown_ticker(ticker_symbol):
                raise_provider_not_found("yfinance", ticker_symbol)
            return MockTicker(ticker_symbol)
        return yf.Ticker(ticker_symbol, **kwargs)

    def download(self, tickers, **kwargs):
        """
        Proxy for yf.download. 
        Supports both single ticker strings and lists of tickers.
        For FX symbols (=X), uses deterministic mock data.
        """
        if self.is_dev:
            start = kwargs.get("start")
            end = kwargs.get("end")
            group_by = kwargs.get("group_by", "column")
            
            # 1. Vereinheitlichen: Mach aus einem String eine Liste
            ticker_list = [tickers] if isinstance(tickers, str) else list(tickers)
            
            # 2. Generiere die einzelnen Mock-DataFrames
            all_dfs = {}
            for t in ticker_list:
                if is_unknown_ticker(t):
                    raise_provider_not_found("yfinance", t)
                # Use FX mock data for symbols ending with =X
                if "=X" in t:
                    all_dfs[t] = _get_mock_fx_data(t, start, end)
                else:
                    all_dfs[t] = generate_mock_ohlcv(t, start=start, end=end, include_holiday_gaps=True)
            
            # 3. Erzeuge das MultiIndex-DataFrame (Standard: Ticker auf Level 0)
            # Struktur hier: [Ticker, Attribute] (das entspricht group_by='ticker')
            combined_df = pd.concat(all_dfs, axis=1)
            
            # Wenn yfinance standardmäßig (group_by='column') aufgerufen wird:
            # Struktur wechseln zu: [Attribute, Ticker]
            if group_by != "ticker":
                combined_df = combined_df.swaplevel(0, 1, axis=1).sort_index(axis=1)
            
            # 4. Simulate live yfinance behavior for FX downloads.
            # Live yfinance returns a MultiIndex DataFrame for single FX symbols like 'EURUSD=X'
            # with price fields on level 0 and the ticker on level 1.
            if not all_dfs:
                return pd.DataFrame()
            return combined_df





        
        # Live Call
        return yf.download(tickers, **kwargs)

# Singleton instance to be imported across the project
my_yf = MyYFinanceProxy()
