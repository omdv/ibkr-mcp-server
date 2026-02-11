"""Pydantic models for ticker data."""
from datetime import datetime
from pydantic import BaseModel, Field

class GreeksData(BaseModel):
  """Model for options greeks data."""

  delta: float | None = Field(None, description="Delta value")
  gamma: float | None = Field(None, description="Gamma value")
  vega: float | None = Field(None, description="Vega value")
  theta: float | None = Field(None, description="Theta value")
  implied_vol: float | None = Field(None, description="Implied volatility")


class TickerData(BaseModel):
  """Model for ticker data."""

  contract_id: int = Field(..., description="Contract ID")
  symbol: str = Field(..., description="Symbol")
  sec_type: str = Field(..., description="Security type")
  last: float | None = Field(None, description="Last price")
  close: float | None = Field(None, description="Close price")
  bid: float | None = Field(None, description="Bid price")
  ask: float | None = Field(None, description="Ask price")
  high: float | None = Field(None, description="High price")
  low: float | None = Field(None, description="Low price")
  volume: int | None = Field(None, description="Volume")
  greeks: GreeksData | None = Field(None, description="Greeks data for options")
  timestamp: str | None = Field(default=None, description="Timestamp")
  market_data_type: int | None = Field(None, description="Market data type")
