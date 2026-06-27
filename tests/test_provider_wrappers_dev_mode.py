from datetime import date
from io import BytesIO
import os
import sys

import pandas as pd
import pytest
import requests


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.utils.eodhd_wrapper import my_eodhd
from src.utils.ishares_wrapper import my_ishares
from src.utils.tiingo_wrapper import my_tiingo
from src.utils.yf_wrapper import my_yf


@pytest.fixture(autouse=True)
def _set_dev_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "dev")


def test_yf_fx_supports_common_20_and_is_deterministic():
    sample = my_yf.COMMON_FX_SYMBOLS
    assert len(sample) >= 20

    symbol = sample[0]
    first = my_yf.download(symbol, start="2026-01-01", end="2026-01-10", threads=False)
    second = my_yf.download(symbol, start="2026-01-01", end="2026-01-10", threads=False)

    pd.testing.assert_frame_equal(first, second)


def test_yf_accepts_arbitrary_fx_ticker_in_dev_mode():
    df = my_yf.download("EURXYZ=X", start="2026-01-01", end="2026-01-10", threads=False)
    assert not df.empty


def test_unknown_ticker_suffix_raises_for_wrappers():
    with pytest.raises(requests.HTTPError):
        my_yf.download("EURUSD_NA=X", start="2026-01-01", end="2026-01-10")

    with pytest.raises(requests.HTTPError):
        my_eodhd.fetch_history("AAPL_NA", api_key="dummy", request_start_date=date(2026, 1, 1))

    with pytest.raises(requests.HTTPError):
        my_tiingo.fetch_history("aapl_NA", api_key="dummy", request_start_date=date(2026, 1, 1))

    with pytest.raises(requests.HTTPError):
        my_ishares.fetch_excel_bytes("332655_NA", currency="USD")


def test_tiingo_and_eodhd_are_deterministic_in_dev_mode():
    eod_a = my_eodhd.fetch_history("AAPL.US", api_key="dummy", request_start_date=date(2026, 1, 1))
    eod_b = my_eodhd.fetch_history("AAPL.US", api_key="dummy", request_start_date=date(2026, 1, 1))
    assert eod_a == eod_b

    tgo_a = my_tiingo.fetch_history("aapl", api_key="dummy", request_start_date=date(2026, 1, 1))
    tgo_b = my_tiingo.fetch_history("aapl", api_key="dummy", request_start_date=date(2026, 1, 1))
    assert tgo_a == tgo_b


def test_ishares_mock_excel_contains_required_sheets():
    excel_bytes = my_ishares.fetch_excel_bytes("332655", currency="USD")
    sheets = pd.read_excel(BytesIO(excel_bytes), sheet_name=["Historisch", "Ausschüttungen"])
    assert "Historisch" in sheets
    assert "Ausschüttungen" in sheets
