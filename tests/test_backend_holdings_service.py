import datetime
import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.services.holdings_service import (
    get_holdings_date_range,
    get_holdings_chart_data,
    get_holdings_display_df,
    get_holdings_reorganization_status,
    get_holdings_records,
    get_holdings_summary,
    run_holdings_reorganization,
    resolve_selected_holdings_date,
)


class StubHoldingsRepository:
    def __init__(self, daily_holdings=None, asset_rows=None, ref_meta=None):
        self.daily_holdings = daily_holdings or []
        self.asset_rows = asset_rows or []
        self.ref_meta = ref_meta or []

    def get_daily_holdings(self, user_id=None, holding_date=None, account_codes=None, isins=None):
        return self.daily_holdings

    def get_all_assets_with_labels(self, isins=None):
        return self.asset_rows

    def get_ref_metadata(self, table_name):
        return self.ref_meta

    def get_user_holdings_min_date(self, user_id=None):
        return datetime.date(2026, 1, 10)

    def get_user_holdings_reorganization_status(self, user_id):
        return {
            "user_id": user_id,
            "last_transaction_modification": "2026-06-30T10:00:00+00:00",
            "last_reorganization": "2026-06-30T09:00:00+00:00",
            "account_count": 2,
        }

    def reorganize_incremental_holdings(self, user_id, account_codes=None, dry_run=False):
        return {
            "user_id": user_id,
            "relevant_accounts_count": 1,
            "transactions_scanned": 10,
            "snapshots_generated": 5,
            "rows_deleted": 1,
            "rows_inserted": 2,
            "rows_updated": 3,
            "rows_unchanged": 4,
            "reorg_timestamp_written": True,
            "reorg_timestamp": "2026-06-30T10:15:00+00:00",
            "dry_run": dry_run,
        }


def test_resolve_selected_holdings_date_falls_back_to_last_date_for_invalid_state():
    first_date = datetime.date(2026, 1, 10)
    last_date = datetime.date(2026, 6, 25)

    assert resolve_selected_holdings_date(None, first_date, last_date) == last_date
    assert resolve_selected_holdings_date(datetime.date(2025, 1, 1), first_date, last_date) == last_date


def test_get_holdings_date_range_returns_first_and_last_dates():
    repository = StubHoldingsRepository()

    result = get_holdings_date_range(
        user_id="user-1",
        today=datetime.date(2026, 7, 1),
        repository=repository,
    )

    assert result == {
        "user_id": "user-1",
        "first_date": datetime.date(2026, 1, 10),
        "last_date": datetime.date(2026, 6, 30),
    }


def test_get_holdings_display_df_merges_asset_labels_and_sorts_rows():
    repository = StubHoldingsRepository(
        daily_holdings=[
            {
                "user_id": "user-1",
                "account_code": "ACC1",
                "holding_date": "2026-06-30",
                "isin": "AAA",
                "quantity": 2.0,
                "price_currency": "USD",
                "price": 100.0,
                "valuation_in_price_currency": 200.0,
                "exchange_rate_to_eur": 1.1,
                "valuation_in_eur": 181.82,
            }
        ],
        asset_rows=[
            {
                "ISIN": "AAA",
                "Name": "Alpha Asset",
                "Ticker": "ALP",
                "Risk Currency": "USD",
                "Type": "ETF",
                "Asset Class": "Equity",
                "Region": "North America",
                "Sector": "Technology",
                "Industry": "Software",
                "Country": "US",
            }
        ],
    )

    df = get_holdings_display_df("user-1", datetime.date(2026, 6, 30), repository=repository)

    assert list(df.columns) == [
        "User ID",
        "Account Code",
        "Holding Date",
        "ISIN",
        "Quantity",
        "Price Currency",
        "Price",
        "Valuation (Price Curr)",
        "FX to EUR",
        "Valuation (EUR)",
        "Asset Name",
        "Asset Ticker",
        "Asset Risk Currency",
        "Asset Type",
        "Asset Class",
        "Asset Region",
        "Asset Sector",
        "Asset Industry",
        "Asset Country",
    ]
    assert df.iloc[0]["Asset Name"] == "Alpha Asset"
    assert df.iloc[0]["Asset Class"] == "Equity"


def test_get_holdings_chart_data_orders_by_reference_metadata():
    repository = StubHoldingsRepository(
        ref_meta=[
            {"label": "Bond", "color_hex": "#222222", "display_order": 2},
            {"label": "Equity", "color_hex": "#111111", "display_order": 1},
        ]
    )

    filtered_df = get_holdings_display_df(
        "user-1",
        datetime.date(2026, 6, 30),
        repository=StubHoldingsRepository(
            daily_holdings=[
                {"user_id": "user-1", "account_code": "ACC1", "holding_date": "2026-06-30", "isin": "AAA", "valuation_in_eur": 200.0},
                {"user_id": "user-1", "account_code": "ACC1", "holding_date": "2026-06-30", "isin": "BBB", "valuation_in_eur": 100.0},
            ],
            asset_rows=[
                {"ISIN": "AAA", "Asset Class": "Bond"},
                {"ISIN": "BBB", "Asset Class": "Equity"},
            ],
        ),
    )

    chart_data, color_by_label = get_holdings_chart_data(
        filtered_df,
        "Asset Class",
        repository=repository,
    )

    assert list(chart_data.index) == ["Equity", "Bond"]
    assert color_by_label == {"Bond": "#222222", "Equity": "#111111"}


def test_get_holdings_records_returns_api_shape():
    repository = StubHoldingsRepository(
        daily_holdings=[
            {
                "user_id": "user-1",
                "account_code": "ACC1",
                "holding_date": "2026-06-30",
                "isin": "AAA",
                "quantity": 2.0,
                "price_currency": "USD",
                "price": 100.0,
                "valuation_in_price_currency": 200.0,
                "exchange_rate_to_eur": 1.1,
                "valuation_in_eur": 181.82,
            }
        ],
        asset_rows=[
            {
                "ISIN": "AAA",
                "Name": "Alpha Asset",
                "Ticker": "ALP",
                "Risk Currency": "USD",
                "Type": "ETF",
                "Asset Class": "Equity",
                "Region": "North America",
                "Sector": "Technology",
                "Industry": "Software",
                "Country": "US",
            }
        ],
    )

    records = get_holdings_records(
        user_id="user-1",
        selected_date=datetime.date(2026, 6, 30),
        repository=repository,
    )

    assert records == [
        {
            "user_id": "user-1",
            "account_code": "ACC1",
            "holding_date": "2026-06-30",
            "isin": "AAA",
            "quantity": 2.0,
            "price_currency": "USD",
            "price": 100.0,
            "valuation_in_price_currency": 200.0,
            "fx_to_eur": 1.1,
            "valuation_in_eur": 181.82,
            "asset_name": "Alpha Asset",
            "asset_ticker": "ALP",
            "asset_risk_currency": "USD",
            "asset_type": "ETF",
            "asset_class": "Equity",
            "asset_region": "North America",
            "asset_sector": "Technology",
            "asset_industry": "Software",
            "asset_country": "US",
        }
    ]


def test_get_holdings_summary_returns_positive_items_with_colors():
    repository = StubHoldingsRepository(
        daily_holdings=[
            {"user_id": "user-1", "account_code": "ACC1", "holding_date": "2026-06-30", "isin": "AAA", "valuation_in_eur": 200.0},
            {"user_id": "user-1", "account_code": "ACC1", "holding_date": "2026-06-30", "isin": "BBB", "valuation_in_eur": 100.0},
        ],
        asset_rows=[
            {"ISIN": "AAA", "Asset Class": "Bond"},
            {"ISIN": "BBB", "Asset Class": "Equity"},
        ],
        ref_meta=[
            {"label": "Bond", "color_hex": "#222222", "display_order": 2},
            {"label": "Equity", "color_hex": "#111111", "display_order": 1},
        ],
    )

    summary = get_holdings_summary(
        user_id="user-1",
        selected_date=datetime.date(2026, 6, 30),
        pie_dimension="Asset Class",
        repository=repository,
    )

    assert summary == {
        "pie_dimension": "Asset Class",
        "total_valuation_eur": 300.0,
        "items": [
            {"label": "Equity", "valuation_eur": 100.0, "color_hex": "#111111"},
            {"label": "Bond", "valuation_eur": 200.0, "color_hex": "#222222"},
        ],
    }


def test_get_holdings_reorganization_status_returns_repository_response():
    repository = StubHoldingsRepository()

    status = get_holdings_reorganization_status(user_id="user-1", repository=repository)

    assert status["user_id"] == "user-1"
    assert status["account_count"] == 2


def test_run_holdings_reorganization_passes_arguments_to_repository():
    repository = StubHoldingsRepository()

    summary = run_holdings_reorganization(
        user_id="user-1",
        account_codes=["ACC1"],
        dry_run=False,
        repository=repository,
    )

    assert summary["user_id"] == "user-1"
    assert summary["rows_inserted"] == 2