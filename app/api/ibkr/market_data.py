"""Contract and options-related tools."""
import json
from fastapi import Query
from fastapi.responses import JSONResponse
from app.api.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger
from app.models import MarketData, BarData

# Module-level query parameter definitions
CONTRACT_IDS_QUERY = Query(default=None, description="List of contract IDs")
FILTERS_QUERY = Query(default=None, description="Filters as JSON string")
CRITERIA_QUERY = Query(default=None, description="Criteria as JSON string")
SEC_TYPE_QUERY = Query(default="STK", description="Security type (used with symbol)")
EXCHANGE_QUERY = Query(default="SMART", description="Exchange (used with symbol)")
CURRENCY_QUERY = Query(default="USD", description="Currency")

@ibkr_router.get(
  "/market_data",
  operation_id="get_market_data",
  response_model=list[MarketData],
)
async def get_market_data(
  contract_ids: list[int] | int | None = CONTRACT_IDS_QUERY,
  symbol: str | None = Query(default=None, description="Symbol to get data for (optional if contract_ids is provided, recommended for better performance)"),
  sec_type: str = SEC_TYPE_QUERY,
  exchange: str = EXCHANGE_QUERY,
  currency: str = CURRENCY_QUERY,
  subscription_type: str = "realtime" 
) -> list[MarketData]:
  """Get market data for a list of contract IDs or symbol.

  This function queries the IB TWS to get the market data for a list of contract IDs
  or a single symbol. If symbol parameters are provided, they will be used to
  resolve the contract ID first.

  Args:
    contract_ids: A list of contract IDs, a single contract ID, or None.
    symbol: Symbol to get data for (optional if contract_ids is provided)
    sec_type: Security type (used with symbol, default: STK)
    exchange: Exchange (used with symbol, default: SMART)
    currency: Currency (used with symbol, default: USD)
    subscription_type: Type of market data subscription (realtime or delayed, default: realtime)

  Returns:
    List[MarketData]: A list of market data for the contract IDs.

  Example:
    >>> curl -X GET "http://localhost:8000/ibkr/market_data?symbol=AAPL&subscription_type=delayed"
    [
      {
        "contract_id": 265598,
        "symbol": "AAPL",
        "sec_type": "STK",
        "last": 263.55,
        "close": 272.95,
        "bid": null,
        "ask": null,
        "bid_size": null,
        "ask_size": null,
        "high": 272.81,
        "low": 262.89,
        "volume": 724566,
        "mark": null,
        "high_52_week": null,
        "low_52_week": null,
        "option_volume": 724566,
        "option_open_interest": null,
        "greeks": null,
        "timestamp": "2026-02-28T12:08:47.821499+00:00",
        "market_data_type": 3
      }
    ]

  """
  # Validate that either symbol or contract_ids is provided
  if not symbol and not contract_ids:
    return JSONResponse(
      status_code=400,
      content={"error": "Either 'symbol' or 'contract_ids' must be provided"}
    )
  
  try:
    logger.debug(
      "Getting market data for contract_ids={contract_ids}, symbol={symbol}",
      contract_ids=contract_ids,
      symbol=symbol,
    )
    market_data = await ib_interface.get_tickers(
      contract_ids=contract_ids,
      symbol=symbol,
      sec_type=sec_type,
      exchange=exchange,
      currency=currency,
      subscription_type=subscription_type
    )
  except Exception as e:
    logger.error("Error in get_market_data: {!s}", str(e))
    return []
  else:
    logger.debug("Market data: {market_data}", market_data=market_data)
    return market_data

@ibkr_router.get(
  "/market_data/filtered_options_chain",
  operation_id="get_filtered_options_chain",
  response_model=list[MarketData],
)
async def get_and_filter_options_chain(
  underlying_symbol: str,
  underlying_sec_type: str,
  underlying_con_id: int,
  filters: str | None = FILTERS_QUERY,
  criteria: str | None = CRITERIA_QUERY,
) -> list[MarketData]:
  """Get and filter option chain based on market data criteria.

  Args:
    underlying_symbol: Symbol of the underlying contract.
    underlying_sec_type: Security type of the underlying contract.
    underlying_con_id: ConID of the underlying contract.
    filters: Filters as JSON string to apply to the options chain,
    you must specify at least one filter to reduce the number of options in the chain,
    you must specify expirations, you can specify tradingClass, strikes, and rights.
      - tradingClass: List of trading classes to filter by.
      - expirations: List of expirations to filter by.
      - strikes: List of strikes to filter by.
      - rights: List of rights to filter by.
    criteria: Criteria as JSON string to filter by.
      - min_delta: Minimum delta value (float)
      - max_delta: Maximum delta value (float)

  Returns:
    list[MarketData]: A list of filtered market data for options.

  Example:
    await get_and_filter_options(
      underlying_symbol="SPX",
      underlying_sec_type="IND",
      underlying_con_id=416904,
      filters='{
        "tradingClass": ["SPXW"],
        "expirations": ["20250505"],
        "strikes": [5490],
        "rights": ["C", "P"],
      }',
      criteria='{"min_delta": -0.06, "max_delta": -0.04}',
    )
    [
      MarketData(symbol='SPXW 250505P05490000', last=45.50, greeks=GreeksData(delta=-0.05)), #noqa: E501
    ]

  """
  try:
    logger.debug(
      f"""
      Getting and filtering options chain for the following parameters:
      underlying_symbol: {underlying_symbol},
      underlying_sec_type: {underlying_sec_type},
      underlying_con_id: {underlying_con_id},
      filters: {filters},
      criteria: {criteria}
      """,
    )
    # Parse JSON strings to dictionaries
    filters_dict = json.loads(filters) if filters else None
    criteria_dict = json.loads(criteria) if criteria else None

    filtered_options = await ib_interface.get_and_filter_options(
      underlying_symbol,
      underlying_sec_type,
      underlying_con_id,
      filters_dict,
      criteria_dict,
    )
  except json.JSONDecodeError as e:
    logger.error("Error parsing JSON parameters: {!s}", str(e))
    return []
  except Exception as e:
    logger.error("Error in filter_options: {!s}", str(e))
    return []
  else:
    logger.debug(
      "Filtered options: {filtered_options}",
      filtered_options=filtered_options,
    )
    return filtered_options


@ibkr_router.get(
  "/market_data/historical",
  operation_id="get_historical_data",
  response_model=list[BarData],
)
async def get_historical_data(
  symbol: str | None = Query(default=None, description="Symbol to get data for (optional if contract_id is provided, recommended for better performance)"),
  contract_id: int | None = Query(default=None, description="Contract ID to get data for (optional if symbol is provided, more efficient than symbol lookup)"),
  sec_type: str = SEC_TYPE_QUERY,
  exchange: str = EXCHANGE_QUERY,
  currency: str = CURRENCY_QUERY,
  duration: str = Query(default="1 D", description="Duration (e.g., '1 D', '1 W', '1 M')"),
  bar_size: str = Query(default="1 min", description="Bar size (e.g., '1 min', '5 mins', '1 hour', '1 day')"),
  what_to_show: str = Query(default="TRADES", description="What to show (TRADES, MIDPOINT, BID, ASK)"),
  use_rth: bool = Query(default=True, description="Use regular trading hours only"),
  end_date: str | None = Query(default=None, description="End date for historical data. Formats: 'YYYYMMDD' (converted to 'YYYYMMDD 15:59:00 {timezone}'), 'YYYYMMDD HH:MM:SS', or 'YYYYMMDD HH:MM:SS Timezone'"),
) -> list[BarData]:
  """Get historical market data.
  
  Retrieve historical OHLCV bar data for a given contract.
  Either symbol or contract_id must be provided. Using contract_id is recommended
  as it avoids an additional symbol lookup and is more efficient.
  
  Args:
    symbol: Symbol to get data for (optional if contract_id is provided)
    contract_id: Contract ID to get data for (optional if symbol is provided)
    sec_type: Security type (STK, OPT, FUT, etc.) - used with symbol
    exchange: Exchange (default: SMART) - used with symbol
    currency: Currency (default: USD)
    duration: Duration string (e.g., '1 D', '1 W', '1 M', '1 Y')
    bar_size: Bar size (e.g., '1 min', '5 mins', '1 hour', '1 day')
    what_to_show: What to show (TRADES, MIDPOINT, BID, ASK)
    use_rth: Use regular trading hours only
    end_date: End date/time for historical data.
      - Date only: 'YYYYMMDD' (e.g., '20260223') - will be converted to 'YYYYMMDD 15:59:00 {timezone}'
      - Date with time: 'YYYYMMDD HH:MM:SS' (e.g., '20260223 15:30:00')
      - Date with time and timezone: 'YYYYMMDD HH:MM:SS Timezone' (e.g., '20260223 15:30:00 US/Eastern')
      
  Returns:
    List of historical bar data
    
  Example with contract_id (recommended):
    >>> await get_historical_data(
    ...   contract_id=265598,
    ...   duration="1 D",
    ...   bar_size="5 mins",
    ...   end_date="20260223"
    ... )
    [
      {
        "date": "2024-01-15T09:30:00",
        "open": 150.25,
        "high": 151.00,
        "low": 150.10,
        "close": 150.75,
        "volume": 125000,
        "wap": 150.50,
        "count": 450
      }
    ]
  
  Example with symbol:
    >>> await get_historical_data(
    ...   symbol="AAPL",
    ...   sec_type="STK",
    ...   duration="1 D",
    ...   bar_size="5 mins"
    ... )
  """
  # Validate that either symbol or contract_id is provided
  if not symbol and not contract_id:
    return JSONResponse(
      status_code=400,
      content={"error": "Either 'symbol' or 'contract_id' must be provided"}
    )
  
  try:
    logger.debug(f"Getting historical data for symbol={symbol}, contract_id={contract_id}")
    bars = await ib_interface.get_historical_data(
      symbol=symbol,
      contract_id=contract_id,
      sec_type=sec_type,
      exchange=exchange,
      currency=currency,
      duration=duration,
      bar_size=bar_size,
      what_to_show=what_to_show,
      use_rth=use_rth,
      end_date=end_date
    )
    return bars
  except Exception as e:
    logger.error(f"Error in get_historical_data: {e}")
    return JSONResponse(
      status_code=500,
      content={"error": str(e), "message": "Failed to get historical data"}
    )


