"""Contract operations."""
import asyncio
from typing import List, Dict, Any

from ib_async import util
from ib_async.contract import Contract, Option

from app.core.setup_logging import logger
from app.util.convert_camel_to_snake_case import (
  convert_df_columns_to_snake_case,
  obj_to_dict_snake_case,
)
from .client import IBClient

class ContractClient(IBClient):
  """Contract operations.

  Available public methods:
    - get_contract_details: get contract details for a given symbol
    - get_options_chain: get options chain for a given underlying contract

  """

  @staticmethod
  def _format_friendly_option_symbol(row: dict) -> str | None:
    """Format a friendly symbol string for option contracts.

    Formats options like: SYMBOL MmmDD'YY STRIKE PUT/CALL
    Example: NEM Dec20'24 42.5 PUT

    Args:
      row: Dictionary containing contract data with keys:
        - sec_type: Security type (e.g., 'OPT')
        - right: Option right ('C', 'P', 'CALL', 'PUT')
        - symbol: Underlying symbol
        - last_trade_date_or_contract_month: Expiry date in YYYYMMDD format
        - strike: Strike price

    Returns:
      Formatted friendly symbol string or None if not an option.
    """
    if row.get('sec_type') == 'OPT' or row.get('right') in ['C', 'P', 'CALL', 'PUT']:
      symbol = row.get('symbol', '')
      last_trade_date = row.get('last_trade_date_or_contract_month', '')
      strike = row.get('strike', '')
      right = row.get('right', '')

      # Format expiry: YYYYMMDD -> MmmDD'YY
      if last_trade_date and len(str(last_trade_date)) >= 8:
        date_str = str(last_trade_date)[:8]
        from datetime import datetime
        dt = datetime.strptime(date_str, '%Y%m%d')
        expiry_formatted = dt.strftime("%b%d'%y").replace(' 0', ' ')
      else:
        expiry_formatted = last_trade_date

      # Format right
      right_formatted = 'CALL' if right in ['C', 'CALL'] else 'PUT' if right in ['P', 'PUT'] else right

      return f"{symbol} {expiry_formatted} {strike} {right_formatted}"
    return None

  async def get_contract_details(
      self,
      symbol: str,
      sec_type: str,
      exchange: str,
      primary_exchange: str | None = None,
      currency: str | None = None,
      options: dict | None = None,
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
    """Get contract details for a given symbol.

    Args:
      symbol: Symbol to get contract details for.
      sec_type: Security type to get contract details for, supported types are:
        - STK: Stock
        - IND: Index
        - CASH: Currency
        - BOND: Bond
        - FUT: Future
        - OPT: Option
      exchange: Exchange to get contract details for, supported exchanges are:
        - CBOE: CBOE
        - NYSE: NYSE
        - ARCA: ARCA
        - BATS: BATS
        - NASDAQ: NASDAQ
      primary_exchange: Primary exchange to get contract details for.
      currency: Currency to get contract details for.
      options: Dictionary of options to get contract details for.
        - strike: Strike price to get contract details for.
        - right: Right to get contract details for.
        - lastTradeDateOrContractMonth: Last trade date or contract month.
        - tradingClass: Trading class to get contract details for.

    Returns:
        Dict of contract details if a single matching contract is found,
        or list of contract candidates if multiple matches are found.

    """
    try:
      await self._connect()

      contract_params = {
        "strike": 0,
        "right": "",
        "lastTradeDateOrContractMonth": "",
        "tradingClass": "",
        "comboLegs": [],
      }
      if options:
        contract_params.update(options)

      contract = Contract(
        conId=0,
        symbol=symbol,
        exchange=exchange or '',
        primaryExchange=primary_exchange or '',
        currency=currency or '',
        secType=sec_type,
        **contract_params,
      )

      while True:
        contracts = await asyncio.wait_for(
            self.ib.qualifyContractsAsync(contract, returnAll=True),
            timeout=self.config.ib_request_timeout,
          )
        if not contracts or contracts[0] is None:
          return []

        # contracts[0] is either a Contract or a list of Contracts (if ambiguous and returnAll=True)
        if isinstance(contracts[0], list):
          contract_list = contracts[0]
          filtered = [
            c
            for c in contract_list
            if c is not None
            and (exchange is None or c.exchange == exchange)
            and (primary_exchange is None or c.primaryExchange == primary_exchange)
            and (currency is None or c.currency == currency)
          ]

          # If we have exactly 1 match, re-qualify with that contract
          if len(filtered) == 1:
            contract = filtered[0]
            continue

          # Convert Contract objects to dicts with snake_case keys
          return [obj_to_dict_snake_case(c) for c in filtered]
        else:
          contracts = convert_df_columns_to_snake_case(util.df(contracts))
          # contracts = contracts[[
          #   "con_id",
          #   "symbol",
          #   "sec_type",
          #   "exchange",
          #   "primary_exchange",
          #   "currency",
          #   "local_symbol",
          #   "multiplier",
          # ]]
          # Return single contract as dict
          return contracts.iloc[0].to_dict()

    except Exception as e:
      logger.error("Error getting contract details: {}", str(e))
      raise

  async def get_options_chain(
    self,
    underlying_symbol: str,
    underlying_sec_type: str,
    underlying_con_id: int,
    exchange: str | None = None,
    filters: dict | None = None,
    ) -> Dict[str, Any] | List[Dict[str, Any]]:
    """Get options chain for a given underlying contract.

    Args:
      underlying_symbol: Symbol of the underlying contract.
      underlying_sec_type: Security type of the underlying contract.
      underlying_con_id: Contract ID of the underlying contract.
      exchange: Exchange to filter chains by (e.g., SMART, CBOE). If not specified
        and multiple chains are available, returns a list of candidate chains.
      filters: Dictionary of filters to apply to the options chain.
        - trading_class: List of trading classes to filter by.
        - expirations: List of expirations to filter by.
        - strikes: List of strikes to filter by.
        - rights: List of rights to filter by.

    Returns:
      Dict of options contracts if a qualified,single chain is found and a filter to reduce the number of options is provided
      or list of candidate chains if multiple matches are found.

    """
    try:
      await self._connect()

      chains = await asyncio.wait_for(
        self.ib.reqSecDefOptParamsAsync(
          underlyingSymbol=underlying_symbol,
          futFopExchange="",
          underlyingSecType=underlying_sec_type,
          underlyingConId=underlying_con_id,
        ),
        timeout=self.config.ib_request_timeout,
      )

      if not chains:
        return []

      # Convert to DataFrame for easier handling
      chains_df = util.df(chains)
      if chains_df is None or chains_df.empty:
        return []

      # Filter chains by exchange if specified
      if exchange is not None:
        filtered_chains = chains_df[chains_df["exchange"] == exchange]
      else:
        filtered_chains = chains_df   
      
      if len(filtered_chains) == 1 and filters: 
        # If we have exactly 1 chain and a filters are specified, generate contracts
        # if no filters, the overall number of contracts can be huge, so we prevent that
        qualified_chain = filtered_chains.iloc[0]

        if not filters:
          raise Exception("Filters are required to reduce the number of contracts.")
        else:
          trading_classes = qualified_chain["tradingClass"]
          # tradingClass is a single string, wrap in list for consistent handling
          if isinstance(trading_classes, str):
            trading_classes = [trading_classes]
          expirations = qualified_chain["expirations"]
          strikes = qualified_chain["strikes"]
          if "trading_class" in filters:
            trading_classes = [tc for tc in trading_classes if tc in filters["trading_class"]]
          if "expirations" in filters:
            expirations = [e for e in expirations if e in filters["expirations"]]
          if "strikes" in filters:
            strikes = [s for s in strikes if s in filters["strikes"]]
          rights = filters.get("rights", ["C", "P"])

          # Generate option contracts using data from selected chain
          contracts = [
            Option(
              symbol=underlying_symbol,
              lastTradeDateOrContractMonth=expiry,
              strike=strike,
              right=right,
              exchange=qualified_chain["exchange"],
              tradingClass=trading_class,
            )
            for right in rights
            for strike in strikes
            for expiry in expirations
            for trading_class in trading_classes
          ]

          try:
            contracts = await asyncio.wait_for(
                self.ib.qualifyContractsAsync(*contracts, returnAll=True),
                timeout=self.config.ib_request_timeout,
              )
            if len(contracts) == 0:
              raise Exception("No contracts found for the given filters.")
            contracts = [c for c in contracts if c is not None]
            if len(contracts) == 0:
              raise Exception("No contracts found for the given filters.")
            contracts_df = convert_df_columns_to_snake_case(util.df(contracts))
            
            # Check if contracts_df is None (util.df can return None for certain inputs)
            if contracts_df is None:
              raise Exception("Failed to convert contracts to DataFrame.")

            if contracts_df.empty:
              raise Exception("No contracts found for the given filters.")
            contracts_df['friendly_symbol'] = contracts_df.apply(self._format_friendly_option_symbol, axis=1)

            # Reorder columns to place friendly_symbol after local_symbol
            if 'local_symbol' in contracts_df.columns and 'friendly_symbol' in contracts_df.columns:
              cols = list(contracts_df.columns)
              local_symbol_idx = cols.index('local_symbol')
              # Remove friendly_symbol from its current position and insert after local_symbol
              cols.remove('friendly_symbol')
              cols.insert(local_symbol_idx + 1, 'friendly_symbol')
              contracts_df = contracts_df[cols]

            return contracts_df.to_dict(orient="records")
          except Exception as e:
            logger.warning("Error qualifying contracts: {}", str(e))
            raise
      else:
        # Return list of candidate chains
        candidate_chains = filtered_chains[[
          "exchange",
          "underlyingConId",
          "tradingClass",
          "expirations",
          "strikes",
        ]]
        return convert_df_columns_to_snake_case(candidate_chains).to_dict(orient="records")

    except Exception as e:
      logger.error("Error getting options chain: {}", str(e))
      raise e
