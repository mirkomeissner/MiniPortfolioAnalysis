import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.services.accounts_service import build_accounts_df


def test_build_accounts_df_returns_expected_columns_for_empty_input():
    df = build_accounts_df([])

    assert list(df.columns) == ["Account Code", "Description"]
    assert df.empty


def test_build_accounts_df_renames_account_fields():
    df = build_accounts_df(
        [{"account_code": "ACC1", "description": "Main account"}]
    )

    assert df.to_dict("records") == [
        {"Account Code": "ACC1", "Description": "Main account"}
    ]


def test_build_accounts_df_normalizes_missing_description_to_none():
    df = build_accounts_df(
        [{"account_code": "ACC1", "description": None}]
    )

    assert df.to_dict("records") == [
        {"Account Code": "ACC1", "Description": None}
    ]