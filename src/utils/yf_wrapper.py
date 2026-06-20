import os
import pandas as pd
import numpy as np
import yfinance as yf

# --- FIXED MOCK FX DATA (NO WEEKENDS, DETERMINISTIC) ---

def _get_mock_fx_data(symbol, start, end):
    """
    Returns fixed mock FX data for testing.
    5 common currency pairs with realistic rates since 2025-01-01.
    Only weekdays (Mon-Fri), no random drops.
    """
    fx_rates = {
        "EURUSD=X": {
            "base_rate": 1.0850,
            "volatility": 0.0002  # Small daily changes
        },
        "EURGBP=X": {
            "base_rate": 0.8650,
            "volatility": 0.0001
        },
        "EURJPY=X": {
            "base_rate": 155.5,
            "volatility": 0.3
        },
        "EURCHF=X": {
            "base_rate": 0.9450,
            "volatility": 0.00015
        },
        "EURSEK=X": {
            "base_rate": 11.50,
            "volatility": 0.02
        }
    }
    
    if symbol not in fx_rates:
        return pd.DataFrame()
    
    s_date = pd.to_datetime(start if start else "2025-01-01")
    e_date = pd.to_datetime(end if end else pd.Timestamp.now())
    
    if s_date > e_date:
        s_date, e_date = e_date, s_date
    
    # Generate only weekdays (Mon-Fri)
    full_range = pd.date_range(start=s_date, end=e_date, freq="D")
    weekdays = full_range[full_range.dayofweek < 5]
    
    # Generate deterministic rates based on date offset
    base_rate = fx_rates[symbol]["base_rate"]
    volatility = fx_rates[symbol]["volatility"]
    
    # Use date ordinal to create deterministic but varied rates
    np.random.seed(42)  # Fixed seed for reproducibility
    rate_adjustments = np.sin(np.arange(len(weekdays)) * 0.1) * volatility
    close_prices = base_rate + rate_adjustments
    
    df = pd.DataFrame({
        "Open": close_prices * 0.9998,
        "High": close_prices * 1.0001,
        "Low": close_prices * 0.9999,
        "Close": close_prices,
        "Volume": 1000000
    }, index=weekdays)
    
    return df

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
                # Use FX mock data for symbols ending with =X
                if "=X" in t:
                    all_dfs[t] = _get_mock_fx_data(t, start, end)
                else:
                    all_dfs[t] = _generate_mock_data(start, end)
            
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
            return combined_df





        
        # Live Call
        return yf.download(tickers, **kwargs)

# Singleton instance to be imported across the project
my_yf = MyYFinanceProxy()
