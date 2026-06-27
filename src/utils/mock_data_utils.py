import hashlib
from datetime import date
from io import BytesIO

import numpy as np
import pandas as pd
import requests


COMMON_EUR_FX_RATES = {
    "EURUSD=X": {"base_rate": 1.0850, "volatility": 0.00020},
    "EURGBP=X": {"base_rate": 0.8650, "volatility": 0.00010},
    "EURJPY=X": {"base_rate": 155.50, "volatility": 0.30000},
    "EURCHF=X": {"base_rate": 0.9450, "volatility": 0.00015},
    "EURSEK=X": {"base_rate": 11.500, "volatility": 0.02000},
    "EURNOK=X": {"base_rate": 11.650, "volatility": 0.02500},
    "EURDKK=X": {"base_rate": 7.4600, "volatility": 0.00300},
    "EURPLN=X": {"base_rate": 4.2800, "volatility": 0.01000},
    "EURCZK=X": {"base_rate": 24.700, "volatility": 0.05000},
    "EURHUF=X": {"base_rate": 397.00, "volatility": 0.80000},
    "EURTRY=X": {"base_rate": 36.400, "volatility": 0.12000},
    "EURRON=X": {"base_rate": 4.9800, "volatility": 0.00800},
    "EURCAD=X": {"base_rate": 1.4700, "volatility": 0.00350},
    "EURAUD=X": {"base_rate": 1.6400, "volatility": 0.00400},
    "EURNZD=X": {"base_rate": 1.7900, "volatility": 0.00450},
    "EURSGD=X": {"base_rate": 1.4650, "volatility": 0.00250},
    "EURHKD=X": {"base_rate": 8.4300, "volatility": 0.01800},
    "EURCNY=X": {"base_rate": 7.8200, "volatility": 0.01000},
    "EURINR=X": {"base_rate": 91.300, "volatility": 0.18000},
    "EURBRL=X": {"base_rate": 6.2500, "volatility": 0.02000},
}


def _stable_seed(*parts) -> int:
    key = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def normalize_date_range(start, end, default_start="2025-01-01"):
    s_date = pd.to_datetime(start if start else default_start)
    e_date = pd.to_datetime(end if end else pd.Timestamp.now())
    if s_date > e_date:
        s_date, e_date = e_date, s_date
    return s_date, e_date


def weekday_index(start, end, default_start="2025-01-01"):
    s_date, e_date = normalize_date_range(start, end, default_start=default_start)
    full_range = pd.date_range(start=s_date, end=e_date, freq="D")
    return full_range[full_range.dayofweek < 5]


def is_unknown_ticker(ticker: str) -> bool:
    if not ticker:
        return True
    normalized = str(ticker).strip().upper()
    if normalized.endswith("=X"):
        normalized = normalized[:-2]
    return normalized.endswith("_NA")


def raise_provider_not_found(provider_name: str, ticker: str):
    response = requests.Response()
    response.status_code = 404
    response._content = b'{"error":"not found"}'
    response.url = f"mock://{provider_name.lower()}/{ticker}"
    raise requests.HTTPError(
        f"404 Client Error: Not Found for {provider_name} ticker '{ticker}'",
        response=response,
    )


def _derive_base_and_vol(symbol: str):
    if symbol in COMMON_EUR_FX_RATES:
        cfg = COMMON_EUR_FX_RATES[symbol]
        return cfg["base_rate"], cfg["volatility"]

    seed = _stable_seed("fx", symbol)
    rng = np.random.default_rng(seed)
    base = float(rng.uniform(0.55, 180.0))
    vol = max(base * float(rng.uniform(0.00005, 0.0015)), 0.00005)
    return base, vol


def generate_mock_ohlcv(symbol: str, start=None, end=None, include_holiday_gaps=False):
    days = weekday_index(start, end)
    if len(days) == 0:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    base_rate, volatility = _derive_base_and_vol(symbol)
    seed = _stable_seed("ohlcv", symbol, str(pd.Timestamp(days[0]).date()), len(days))
    rng = np.random.default_rng(seed)

    signal = np.sin(np.arange(len(days)) * 0.17) * volatility
    jitter = rng.normal(0.0, volatility * 0.15, size=len(days))
    close = np.maximum(base_rate + signal + jitter, 0.0001)

    if include_holiday_gaps and len(days) > 2:
        keep_mask = rng.choice([True, False], size=len(days), p=[0.95, 0.05])
        keep_mask[0] = True
        days = days[keep_mask]
        close = close[keep_mask]

    open_price = close * (1 - rng.uniform(0.0001, 0.0004, size=len(close)))
    high_price = close * (1 + rng.uniform(0.0001, 0.0005, size=len(close)))
    low_price = close * (1 - rng.uniform(0.0001, 0.0005, size=len(close)))
    volume = rng.integers(1000, 12000, size=len(close))

    return pd.DataFrame(
        {
            "Open": np.round(open_price, 6),
            "High": np.round(high_price, 6),
            "Low": np.round(low_price, 6),
            "Close": np.round(close, 6),
            "Volume": volume,
        },
        index=days,
    )


def generate_eod_rows(ticker: str, start=None, end=None):
    df = generate_mock_ohlcv(ticker, start=start, end=end, include_holiday_gaps=False)
    return [
        {
            "date": idx.date().isoformat(),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "adjusted_close": float(row["Close"]),
            "volume": int(row["Volume"]),
        }
        for idx, row in df.iterrows()
    ]


def generate_tiingo_rows(ticker: str, start=None, end=None):
    df = generate_mock_ohlcv(ticker, start=start, end=end, include_holiday_gaps=False)
    rows = []
    for idx, row in df.iterrows():
        rows.append(
            {
                "date": f"{idx.date().isoformat()}T00:00:00.000Z",
                "close": float(row["Close"]),
                "divCash": 0.0,
                "splitFactor": 1.0,
            }
        )
    return rows


def generate_ishares_excel_bytes(ticker: str, start=None, end=None, currency="USD"):
    df = generate_mock_ohlcv(ticker, start=start, end=end, include_holiday_gaps=False)

    historisch = pd.DataFrame(
        {
            "per": [idx.date().isoformat() for idx in df.index],
            "Währung": currency,
            "NAV": [float(v) for v in df["Close"]],
        }
    )

    aussch = pd.DataFrame({"Ex-Tag": [], "Gesamtausschüttung": []})

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        historisch.to_excel(writer, index=False, sheet_name="Historisch")
        aussch.to_excel(writer, index=False, sheet_name="Ausschüttungen")
    return buffer.getvalue()
