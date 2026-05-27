import os
import pandas as pd
import numpy as np
import yfinance as yf

# --- MOCK DATA GENERATOR ---

def _generate_mock_data(start, end):
    """
    Helper to create synthetic price dataframes with realistic market gaps.
    Simulates missing data for weekends (standard) and random holidays.
    """
    s_date = pd.to_datetime(start if start else (pd.Timestamp.now() - pd.Timedelta(days=30)))
    e_date = pd.to_datetime(end if end else pd.Timestamp.now())
    
    if s_date > e_date:
        s_date, e_date = e_date, s_date
        
    # 1. Create a full range of calendar days
    full_range = pd.date_range(start=s_date, end=e_date, freq="D")
    
    # 2. Filter out weekends (Saturday = 5, Sunday = 6)
    # This is exactly what yfinance does for FX and Stocks
    trading_days = full_range[full_range.dayofweek < 5]
    
    # 3. Optional: Randomly drop a few more days (simulating holidays)
    # 5% chance that a trading day is "missing"
    mask = np.random.choice([True, False], size=len(trading_days), p=[0.95, 0.05])
    trading_days = trading_days[mask]
    
    # 4. Generate the data only for those specific trading days
    df = pd.DataFrame({
        "Open": np.round(np.random.uniform(1.0, 1.2, size=len(trading_days)), 6),
        "High": np.round(np.random.uniform(1.0, 1.2, size=len(trading_days)), 6),
        "Low": np.round(np.random.uniform(1.0, 1.2, size=len(trading_days)), 6),
        "Close": np.round(np.random.uniform(1.0, 1.2, size=len(trading_days)), 6),
        "Volume": np.random.randint(1000, 10000, size=len(trading_days))
    }, index=trading_days)
    
    return df

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
            group_by = kwargs.get("group_by", "column")
            
            # 1. Vereinheitlichen: Mach aus einem String eine Liste
            ticker_list = [tickers] if isinstance(tickers, str) else list(tickers)
            
            # 2. Generiere die einzelnen Mock-DataFrames
            all_dfs = {}
            for t in ticker_list:
                all_dfs[t] = _generate_mock_data(start, end)
            
            # 3. Erzeuge das MultiIndex-DataFrame (Standard: Ticker auf Level 0)
            # Struktur hier: [Ticker, Attribute] (das entspricht group_by='ticker')
            combined_df = pd.concat(all_dfs, axis=1)
            
            # Wenn yfinance standardmäßig (group_by='column') aufgerufen wird:
            # Struktur wechseln zu: [Attribute, Ticker]
            if group_by != "ticker":
                combined_df = combined_df.swaplevel(0, 1, axis=1).sort_index(axis=1)
            
            # 4. yfinance-Spezialverhalten für einzelne Ticker simulieren:
            # Wenn nur ein Ticker angefragt wurde UND keep_multiindex NICHT True ist,
            # bricht yfinance den MultiIndex auf ein normales DataFrame herunter.
            if len(ticker_list) == 1 and not kwargs.get("keep_multiindex", False):
                if group_by == "ticker":
                    # Droppt das Attribut-Level, behält Ticker als Spalten? Nein, umgekehrt:
                    return combined_df.xs(ticker_list[0], axis=1, level=0)
                else:
                    return combined_df.xs(ticker_list[0], axis=1, level=1)
                    
            return combined_df
        
        # Live Call
        return yf.download(tickers, **kwargs)

# Singleton instance to be imported across the project
my_yf = MyYFinanceProxy()
