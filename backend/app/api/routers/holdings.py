import datetime

from fastapi import APIRouter

import pandas as pd

from backend.app.api.schemas.holdings import (
    HoldingsDateRangeResponse,
    HoldingRecord,
    HoldingsReorganizationRequest,
    HoldingsReorganizationResponse,
    HoldingsReorganizationStatusResponse,
)
from backend.app.api.schemas.holdings_summary import HoldingSummaryResponse
from backend.app.services.holdings_service import (
    get_holdings_date_range,
    get_holdings_records,
    get_holdings_reorganization_status,
    get_holdings_summary,
    run_holdings_reorganization,
)


router = APIRouter(prefix="/holdings", tags=["holdings"])


@router.get("/date-range", response_model=HoldingsDateRangeResponse)
def get_date_range(user_id: str) -> HoldingsDateRangeResponse:
    result = get_holdings_date_range(user_id=user_id)
    return {
        "user_id": user_id,
        "first_date": result.get("first_date").isoformat() if result.get("first_date") is not None else None,
        "last_date": result.get("last_date").isoformat(),
    }


@router.get("", response_model=list[HoldingRecord])
def list_holdings(user_id: str, holding_date: datetime.date) -> list[HoldingRecord]:
    return get_holdings_records(user_id=user_id, selected_date=holding_date)


@router.get("/summary", response_model=HoldingSummaryResponse)
def get_holdings_pie_summary(
    user_id: str,
    holding_date: datetime.date,
    pie_dimension: str,
) -> HoldingSummaryResponse:
    return get_holdings_summary(
        user_id=user_id,
        selected_date=holding_date,
        pie_dimension=pie_dimension,
    )


@router.get("/reorganization-status", response_model=HoldingsReorganizationStatusResponse)
def get_reorganization_status(user_id: str) -> HoldingsReorganizationStatusResponse:
    status = get_holdings_reorganization_status(user_id=user_id)
    if status is None:
        return {
            "user_id": user_id,
            "last_transaction_modification": None,
            "last_reorganization": None,
            "account_count": 0,
        }

    return {
        "user_id": status.get("user_id"),
        "last_transaction_modification": (
            pd.to_datetime(status.get("last_transaction_modification"), errors="coerce").isoformat()
            if status.get("last_transaction_modification") is not None
            else None
        ),
        "last_reorganization": (
            pd.to_datetime(status.get("last_reorganization"), errors="coerce").isoformat()
            if status.get("last_reorganization") is not None
            else None
        ),
        "account_count": status.get("account_count"),
    }


@router.post("/reorganize", response_model=HoldingsReorganizationResponse)
def run_reorganization(payload: HoldingsReorganizationRequest) -> HoldingsReorganizationResponse:
    summary = run_holdings_reorganization(
        user_id=payload.user_id,
        account_codes=payload.account_codes,
        dry_run=payload.dry_run,
    )
    return {
        **summary,
        "reorg_timestamp": (
            pd.to_datetime(summary.get("reorg_timestamp"), errors="coerce").isoformat()
            if summary.get("reorg_timestamp") is not None
            else None
        ),
    }