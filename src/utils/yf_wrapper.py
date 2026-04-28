import os
import pandas as pd
import numpy as np
import yfinance as yf

# --- MOCK DATA GENERATOR ---

def _generate_mock_data(start, end):
    """
    Helper to create synthetic price dataframes.
    Simulates daily closing prices and volume.
    """
    s_date = pd.to_datetime(start if start else (pd.Timestamp.now() - pd.Timedelta(days=30)))
    e_date = pd.to_datetime(end if end else pd.Timestamp.now())
    
    if s_date > e_date:
        s_date, e_date = e_date, s_date
        
    dates = pd.date_range(start=s_date, end=e_date, freq="D")
    
    return pd.DataFrame({
        "Open": np.round(np.random.uniform(1.0, 1.2, size=len(dates)), 6),
        "High": np.round(np.random.uniform(1.0, 1.2, size=len(dates)), 6),
        "Low": np.round(np.random.uniform(1.0, 1.2, size=len(dates)), 6),
        "Close": np.round(np.random.uniform(1.0, 1.2, size=len(dates)), 6),
        "Volume": np.random.randint(1000, 10000, size=len(dates))
    }, index=dates)

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
        return _generate_mock_data(kwargs.get("start"), kwargs.get("end"))

class MockSearch:
    """Simulates the yf.Search object."""
    def __init__(self, query):
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
            return MockTicker(ticker_symbol)
        return yf.Ticker(ticker_symbol, **kwargs)

    def download(self, tickers, **kwargs):
        """
        Proxy for yf.download. 
        Supports both single ticker strings and lists of tickers.
        """
        if self.is_dev:
            start = kwargs.get("start")
            end = kwargs.get("end")
            
            # Handle single ticker string
            if isinstance(tickers, str):
                return _generate_mock_data(start, end)
            
            # Handle multiple tickers: yfinance returns a MultiIndex DataFrame
            # Structure: [Attribute (Close, Open...), Ticker]
            all_dfs = {}
            for t in tickers:
                all_dfs[t] = _generate_mock_data(start, end)
            
            # Concatenate along columns to create MultiIndex structure
            combined_df = pd.concat(all_dfs, axis=1)
            
            # Ensure the structure matches yfinance (Ticker is the second level)
            # yf.download(group_by='ticker') usually produces [Ticker, PriceColumn]
            if kwargs.get("group_by") == "ticker":
                return combined_df
            
            # Default yfinance behavior: [PriceColumn, Ticker]
            return combined_df.swaplevel(0, 1, axis=1).sort_index(axis=1)
        
        # Live Call
        return yf.download(tickers, **kwargs)

# Singleton instance to be imported across the project
my_yf = MyYFinanceProxy()
