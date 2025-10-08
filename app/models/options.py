"""Pydantic models for options chain requests."""
from pydantic import BaseModel, Field

class OptionsFilters(BaseModel):
  """Filters to apply to the options chain."""

  expirations: list[str] = Field(
    ...,
    description="List of expiration dates in YYYYMMDD format (required)",
  )
  trading_class: list[str] | None = Field(
    default=None,
    alias="tradingClass",
    description="List of trading classes to filter by",
  )
  strikes: list[float] | None = Field(
    default=None,
    description="List of strike prices to filter by",
  )
  rights: list[str] | None = Field(
    default=None,
    description="List of rights to filter by (C for calls, P for puts)",
  )

  class Config:
    """Config for options filters."""

    populate_by_name = True


class OptionsCriteria(BaseModel):
  """Market data criteria to filter options by."""

  min_delta: float | None = Field(default=None,description="Minimum delta value")
  max_delta: float | None = Field(default=None,description="Maximum delta value")
  min_gamma: float | None = Field(default=None,description="Minimum gamma value")
  max_gamma: float | None = Field(default=None,description="Maximum gamma value")
  min_theta: float | None = Field(default=None,description="Minimum theta value")
  max_theta: float | None = Field(default=None,description="Maximum theta value")
  min_vega: float | None = Field(default=None,description="Minimum vega value")
  max_vega: float | None = Field(default=None,description="Maximum vega value")


class OptionsRequest(BaseModel):
  """Request model for filtered options chain endpoint."""

  underlying_symbol: str = Field(
    ...,
    description="Symbol of the underlying contract",
  )
  underlying_sec_type: str = Field(
    ...,
    description="Security type of the underlying contract",
  )
  underlying_con_id: int = Field(
    ...,
    description="Contract ID of the underlying contract",
  )
  filters: OptionsFilters = Field(
    ...,
    description="Filters to apply to the options chain",
  )
  criteria: OptionsCriteria | None = Field(
    default=None,
    description="Optional market data criteria to filter by",
  )
