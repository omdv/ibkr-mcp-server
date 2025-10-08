"""Contract and options-related tools."""
import json
from fastapi import Query
from app.api.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger
from app.models import TickerData

# Module-level query parameter definitions
FILTERS_QUERY = Query(default=None, description="Filters as JSON string")
CRITERIA_QUERY = Query(default=None, description="Criteria as JSON string")

@ibkr_router.get(
  "/tickers",
  operation_id="get_tickers",
  response_model=list[TickerData],
)
async def get_tickers(
  contract_ids: str | None = None,
) -> list[TickerData]:
  """Get tickers for a list of contract IDs.

  This function queries the IB TWS to get the tickers for a list of contract IDs.
  It will return the last price and symbol, and greeks (if applicable).

  Args:
    contract_ids (str): Comma-separated list of contract IDs to get tickers for.

  Returns:
    List[dict]: A list of ticker dictionaries for the contract IDs.
    will include the contractId, symbol, secType, last, bid, ask, and greeks.

  Example:
    await get_tickers("123456,789012")
    [
      {
        "symbol": "AAPL",
        "last": 150.75,
        "greeks": {
          "delta": 0.5,
        },
      },
      {
        "symbol": "MSFT",
        "last": 210.22,
        "greeks": null,
      },
    ]

  """
  try:
    if contract_ids:
      contract_ids_list = [
        int(cid.strip()) for cid in contract_ids.split(",") if cid.strip()
      ]
    else:
      contract_ids_list = None

    logger.debug(
      "Getting tickers for contract IDs: {contract_ids_list}",
      contract_ids_list=contract_ids_list,
    )
    tickers = await ib_interface.get_tickers(contract_ids_list)
  except Exception as e:
    logger.error("Error in get_tickers: {!s}", str(e))
    return []
  else:
    logger.debug("Tickers: {tickers}", tickers=tickers)
    return tickers

@ibkr_router.get(
  "/filtered_options_chain",
  operation_id="get_filtered_options_chain",
  response_model=list[TickerData],
)
async def get_and_filter_options_chain(
  underlying_symbol: str,
  underlying_sec_type: str,
  underlying_con_id: int,
  filters: str | None = FILTERS_QUERY,
  criteria: str | None = CRITERIA_QUERY,
) -> list[TickerData]:
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
    list[TickerData]: A list of filtered ticker data for options.

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
      TickerData(symbol='SPXW 250505P05490000', last=45.50, greeks=GreeksData(delta=-0.05)), #noqa: E501
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
