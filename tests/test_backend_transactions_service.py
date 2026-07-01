import os
import sys
from unittest.mock import Mock


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.services.transactions_service import build_transactions_df
from backend.app.services.transactions_service import create_transaction
from backend.app.services.transactions_service import create_transactions_bulk
from backend.app.services.transactions_service import delete_all_transactions_for_user
from backend.app.services.transactions_service import get_existing_ids_for_bulk_import
from backend.app.services.transactions_service import get_missing_isins_for_import
from backend.app.services.transactions_service import get_next_transaction_count_for_import
from backend.app.services.transactions_service import get_user_import_settings
from backend.app.services.transactions_service import save_user_import_settings
from backend.app.services.transactions_service import build_transaction_import_preview
from backend.app.services.transactions_service import import_transactions_from_preview


def test_build_transactions_df_returns_expected_columns_for_empty_input():
    df = build_transactions_df([])

    assert list(df.columns) == [
        "Trade Date",
        "Account",
        "ISIN",
        "Name",
        "Type",
        "Quantity",
        "Settle Amount",
        "Settle Curr",
        "FX Rate",
        "Amount (EUR)",
        "Created At",
        "Updated At",
        "Internal ID",
    ]
    assert df.empty


def test_build_transactions_df_maps_joined_labels_for_display():
    df = build_transactions_df(
        [
            {
                "id": "AAA_20260630_000",
                "date": "2026-06-30",
                "account_code": "ACC1",
                "isin": "AAA",
                "transaction_type_code": "BUY",
                "quantity": 2.0,
                "settle_amount": 100.0,
                "settle_currency": "USD",
                "settle_fxrate": 1.1,
                "amount_eur": 90.9,
                "created_at": "2026-06-30T12:00:00",
                "updated_at": "2026-06-30T12:30:00",
                "accounts": {"description": "Main Account"},
                "ref_transaction_type": {"label": "Buy"},
                "asset_static_data": {"name": "Alpha Asset"},
            }
        ]
    )

    assert df.iloc[0]["Account"] == "Main Account"
    assert df.iloc[0]["Name"] == "Alpha Asset"
    assert df.iloc[0]["Type"] == "Buy"


def test_create_transaction_calls_repository_and_returns_payload():
    repository = Mock()
    payload = {
        "user_id": "user-1",
        "id": "AAA_20260630_000",
        "account_code": "ACC1",
        "isin": "AAA",
        "date": "2026-06-30",
        "transaction_type_code": "BUY",
    }

    result = create_transaction(payload, repository=repository)

    repository.save_transaction.assert_called_once_with(payload)
    assert result == payload


def test_create_transaction_generates_id_when_missing():
    repository = Mock()
    repository.get_next_transaction_count.return_value = 7
    payload = {
        "user_id": "user-1",
        "account_code": "ACC1",
        "isin": "AAA",
        "date": "2026-06-30",
        "transaction_type_code": "BUY",
    }

    result = create_transaction(payload, repository=repository)

    repository.get_next_transaction_count.assert_called_once_with(
        user_id="user-1",
        isin="AAA",
        date_str="2026-06-30",
    )
    repository.save_transaction.assert_called_once()
    saved_payload = repository.save_transaction.call_args.args[0]
    assert saved_payload["id"] == "AAA_20260630_007"
    assert result["id"] == "AAA_20260630_007"


def test_create_transactions_bulk_calls_repository_and_returns_count():
    repository = Mock()
    transactions = [
        {"id": "AAA_20260630_000", "user_id": "user-1"},
        {"id": "AAA_20260630_001", "user_id": "user-1"},
    ]

    result = create_transactions_bulk(transactions, repository=repository)

    repository.save_transactions_bulk.assert_called_once_with(transactions)
    assert result == {"saved_count": 2}


def test_get_user_import_settings_returns_repository_value():
    repository = Mock()
    repository.get_import_settings.return_value = {"map_isin": "ISIN"}

    result = get_user_import_settings("user-1", "ACC1", repository=repository)

    repository.get_import_settings.assert_called_once_with(user_id="user-1", account_code="ACC1")
    assert result == {"map_isin": "ISIN"}


def test_save_user_import_settings_calls_repository_and_returns_ack():
    repository = Mock()
    config = {"map_isin": "ISIN", "map_date": "Date"}

    result = save_user_import_settings("user-1", "ACC1", config, repository=repository)

    repository.save_import_settings.assert_called_once_with(
        user_id="user-1",
        account_code="ACC1",
        mapping_config=config,
    )
    assert result == {"user_id": "user-1", "account_code": "ACC1", "saved": True}


def test_delete_all_transactions_for_user_calls_repository_and_returns_ack():
    repository = Mock()

    result = delete_all_transactions_for_user("user-1", repository=repository)

    repository.delete_all_transactions_for_user.assert_called_once_with("user-1")
    assert result == {"user_id": "user-1", "deleted": True}


def test_get_existing_ids_for_bulk_import_calls_repository():
    repository = Mock()
    repository.get_existing_ids_for_bulk.return_value = ["AAA_20260630_000"]

    result = get_existing_ids_for_bulk_import(
        user_id="user-1",
        isins=["AAA"],
        dates=["2026-06-30"],
        repository=repository,
    )

    repository.get_existing_ids_for_bulk.assert_called_once_with(
        user_id="user-1",
        isins=["AAA"],
        dates=["2026-06-30"],
    )
    assert result == ["AAA_20260630_000"]


def test_get_missing_isins_for_import_calls_repository():
    repository = Mock()
    repository.get_missing_isins.return_value = ["BBB"]

    result = get_missing_isins_for_import(["AAA", "BBB"], repository=repository)

    repository.get_missing_isins.assert_called_once_with(["AAA", "BBB"])
    assert result == ["BBB"]


def test_get_next_transaction_count_for_import_calls_repository():
    repository = Mock()
    repository.get_next_transaction_count.return_value = 3

    result = get_next_transaction_count_for_import(
        user_id="user-1",
        isin="AAA",
        date_str="2026-06-30",
        repository=repository,
    )

    repository.get_next_transaction_count.assert_called_once_with(
        user_id="user-1",
        isin="AAA",
        date_str="2026-06-30",
    )
    assert result == 3


def test_build_transaction_import_preview_parses_rows_and_computes_checks():
    repository = Mock()
    repository.get_missing_isins.return_value = ["BBB"]
    repository.get_existing_ids_for_bulk.return_value = ["AAA_20260630_000"]

    csv_content = "\n".join(
        [
            "isin,date,type,quantity,settle_amount,settle_currency",
            "AAA,2026-06-30,BUY,2,100,USD",
            "BBB,2026-06-30,SELL,1,50,EUR",
        ]
    )
    mapping = {
        "map_isin": "isin",
        "map_date": "date",
        "map_type": "type",
        "map_quantity": "quantity",
        "map_settle_amount": "settle_amount",
        "map_settle_currency": "settle_currency",
    }

    result = build_transaction_import_preview(
        user_id="user-1",
        account_code="ACC1",
        csv_content=csv_content,
        mapping_config=mapping,
        repository=repository,
    )

    assert len(result["rows"]) == 2
    assert result["rows"][0]["transaction_type_code"] == "BUY"
    assert result["rows"][0]["amount_eur"] == 100.0
    assert result["missing_isins"] == ["BBB"]
    assert result["existing_ids"] == ["AAA_20260630_000"]
    assert result["duplicate_overlap_count"] == 1


def test_import_transactions_from_preview_skips_overlaps_and_generates_ids():
    repository = Mock()
    repository.get_existing_ids_for_bulk.return_value = ["AAA_20260630_000"]
    repository.get_next_transaction_count.return_value = 1

    rows = [
        {
            "account_code": "ACC1",
            "isin": "AAA",
            "date": "2026-06-30",
            "transaction_type_code": "BUY",
            "quantity": 2.0,
            "settle_amount": 100.0,
            "settle_currency": "USD",
            "settle_fxrate": 1.0,
            "amount_eur": 100.0,
        },
        {
            "account_code": "ACC1",
            "isin": "BBB",
            "date": "2026-06-30",
            "transaction_type_code": "BUY",
            "quantity": 1.0,
            "settle_amount": 50.0,
            "settle_currency": "EUR",
            "settle_fxrate": 1.0,
            "amount_eur": 50.0,
        },
    ]

    result = import_transactions_from_preview(
        user_id="user-1",
        rows=rows,
        duplicate_strategy="skip",
        repository=repository,
    )

    assert result == {"saved_count": 1, "skipped_overlap_count": 1}
    repository.save_transactions_bulk.assert_called_once()
    saved_rows = repository.save_transactions_bulk.call_args.args[0]
    assert saved_rows[0]["id"] == "BBB_20260630_001"