import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.components.asset_management import _is_missing_value


def test_is_missing_value_treats_none_and_nan_as_missing():
    assert _is_missing_value(None) is True
    assert _is_missing_value(float("nan")) is True
    assert _is_missing_value("nan") is True


def test_is_missing_value_treats_real_closed_date_as_present():
    assert _is_missing_value("2026-06-30") is False