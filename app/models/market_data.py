"""Pydantic models for market data."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class BarData(BaseModel):
  """Historical bar data."""

  date: str = Field(..., description="Bar date/time")
  open: float = Field(..., description="Open price")
  high: float = Field(..., description="High price")
  low: float = Field(..., description="Low price")
  close: float = Field(..., description="Close price")
  volume: int = Field(..., description="Volume")
  wap: float | None = Field(None, description="Weighted average price")
  count: int | None = Field(None, description="Trade count")


class HistoricalDataRequest(BaseModel):
  """Request for historical market data."""

  symbol: str = Field(..., description="Symbol")
  sec_type: str = Field(default="STK", description="Security type")
  exchange: str = Field(default="SMART", description="Exchange")
  currency: str = Field(default="USD", description="Currency")
  duration: str = Field(default="1 D", description="Duration (e.g., '1 D', '1 W', '1 M')")
  bar_size: str = Field(default="1 min", description="Bar size (e.g., '1 min', '5 mins', '1 hour', '1 day')")
  what_to_show: str = Field(default="TRADES", description="What to show (TRADES, MIDPOINT, BID, ASK)")
  use_rth: bool = Field(default=True, description="Use regular trading hours only")
