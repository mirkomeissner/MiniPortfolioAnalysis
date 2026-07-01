from pydantic import BaseModel


class HoldingSummaryItem(BaseModel):
    label: str
    valuation_eur: float
    color_hex: str | None = None


class HoldingSummaryResponse(BaseModel):
    pie_dimension: str
    total_valuation_eur: float
    items: list[HoldingSummaryItem]