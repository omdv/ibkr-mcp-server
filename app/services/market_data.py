"""Market data operations."""
import asyncio
import pandas as pd
import exchange_calendars as ecals
import datetime as dt
from ib_async import util
from ib_async.contract import Contract

from .client import IBClient
from .contracts import ContractClient
from app.api.ibkr.ib_constants import LIVE, FROZEN, DELAYED, DELAYED_FROZEN
from app.core.setup_logging import logger
from app.models import MarketData, GreeksData, BarData

class MarketDataClient(IBClient):
  """Market data operations."""

  def __init__(self) -> None:
    """Initialize the MarketDataClient."""
    super().__init__()
    self.contract_client = ContractClient()
    self.contract_client.ib = self.ib

  def _get_session_close(self, liquid_hours: str, target_date: str) -> str | None:
    """Parse the liquidHours string to get the closing time for a target date.
    
    Args:
      liquid_hours: The liquidHours string from contract details (e.g., "20250220:0900-1600;20250221:CLOSED")
      target_date: The target date in YYYYMMDD format
      
    Returns:
      The closing time as HHMM string (e.g., "1600"), or None if the market is closed that day
    """
    if not liquid_hours:
      return None
      
    sessions = liquid_hours.split(';')
    
    for session in sessions:
      if not session:
        continue
        
      # Check if this session matches the target date
      if session.startswith(target_date):
        # Check if market is closed
        if "CLOSED" in session:
          return None
        
        # Extract the hours part (format: "YYYYMMDD:HHMM-HHMM")
        if ':' in session:
          _, hours = session.split(':')
          if '-' in hours:
            _, close_time = hours.split('-')
            return close_time.strip()
    
    return None

  def _is_market_open(self, exchange : str = 'NYSE') -> bool:
      """Check if the market is open."""
      try:
        calendar = ecals.get_calendar(exchange)
        return calendar.is_trading_minute(dt.datetime.now(dt.UTC))
      except Exception as e:
        logger.error(f"Error checking market status: {e}")
        return False

  def _valid_value(self, value, value_type: type):
    """Validate and convert a value to the specified type.
    
    Args:
      value: The value to validate
      value_type: The type to convert to (float or int)
      
    Returns:
      The valid value as the specified type
      None: If the value cannot be converted or is invalid (nan, inf, etc.)
    """
    if not value:
      return None
    if str(value).lower() in ['nan', 'inf', '-inf', '-1', '-1.0', '-2.0']:
      return None
    try:
      return value_type(value)
    except (ValueError, TypeError):
      return None

  def _get_ticker_fields(self, ticker) -> dict:
      """Extract all comparable fields from a ticker object for change detection.
      
      Returns a dictionary of field names to values, excluding methods and private attributes.
      """
      fields = {}
      for attr in dir(ticker):
          # Skip private attributes, methods, and special attributes
          if attr.startswith('_'):
              continue
          # Skip methods
          if callable(getattr(ticker, attr, None)):
              continue
          # Get the value
          value = getattr(ticker, attr)
          # Skip event-like attributes (they have .wait() method)
          if hasattr(value, 'wait') and hasattr(value, 'clear'):
              continue
          fields[attr] = value
      return fields

  def _process_tickers(self, tickers: list[dict]) -> list[MarketData]:
    """Process tickers to extract required fields."""
    result = util.df(tickers)
    result["contract_id"] = result["contract"].apply(lambda x: x.conId)
    result["symbol"] = result["contract"].apply(lambda x: x.localSymbol)
    result["sec_type"] = result["contract"].apply(lambda x: x.secType)
    result["greeks"] = result.apply(self._greek_extraction, axis=1)
    result["timestamp"] = result["time"].apply(lambda x: x.isoformat() if x else None)
    result["market_data_type"] = result["marketDataType"]

    # Convert DataFrame to list of Pydantic models
    ticker_list = []
    for _, row in result.iterrows():
      ticker_data = MarketData(
        contract_id=row["contract_id"],
        symbol=row["symbol"],
        sec_type=row["sec_type"],
        last=self._valid_value(row.get("last"), float),
        close=self._valid_value(row.get("close"), float),
        bid=self._valid_value(row.get("bid"), float),
        ask=self._valid_value(row.get("ask"), float),
        bid_size=self._valid_value(row.get("bidSize"), int),
        ask_size=self._valid_value(row.get("askSize"), int),
        high=self._valid_value(row.get("high"), float),
        low=self._valid_value(row.get("low"), float),
        volume=self._valid_value(row.get("volume"), int),
        mark=self._valid_value(row.get("mark"), float),
        high_52_week=self._valid_value(row.get("high52"), float),
        low_52_week=self._valid_value(row.get("low52"), float),
        option_volume=self._valid_value(row.get("volume"), int),  # Generic tick 100
        option_open_interest=self._valid_value(row.get("openInterest"), int),  # Generic tick 101
        greeks=row["greeks"],
        timestamp=row["timestamp"] or "",
        market_data_type=row["market_data_type"],
      )
      ticker_list.append(ticker_data)

    return ticker_list

  def _greek_extraction(self, ticker: pd.Series) -> GreeksData | None:
    """Extract greeks from a ticker.

    Only extract greeks for options contracts, use modelGreeks.
    Invalid values (null, -1, -2, etc.) are filtered out.
    """
    if (
      ticker.sec_type == "OPT" and
      hasattr(ticker, "modelGreeks") and
      ticker.modelGreeks
    ):
      delta = self._valid_value(ticker.modelGreeks.delta, float)
      gamma = self._valid_value(ticker.modelGreeks.gamma, float)
      vega = self._valid_value(ticker.modelGreeks.vega, float)
      theta = self._valid_value(ticker.modelGreeks.theta, float)
      implied_vol = self._valid_value(ticker.modelGreeks.impliedVol, float)
      
      # Only return GreeksData if at least one value is valid
      if delta is not None or gamma is not None or vega is not None or theta is not None or implied_vol is not None:
        return GreeksData(
          delta=delta,
          gamma=gamma,
          vega=vega,
          theta=theta,
          implied_vol=implied_vol,
        )
    return None

  async def get_tickers(
    self,
    symbol: str,
    sec_type: str,
    exchange: str,
    currency: str,
    contract_ids: list[int] | int | None,
    market_data_subscription_type: str = "realtime"
  ) -> list[dict]:
    """Get tickers for a list of contract IDs, single contract ID, or symbol.

    Args:
        contract_ids: List of contract IDs, a single contract ID, or None.
        symbol: Symbol to get data for (optional if contract_ids is provided).
          If provided, will be resolved to contract_id.
        sec_type: Security type (used with symbol, default: STK)
        exchange: Exchange (used with symbol, default: SMART)
        currency: Currency (used with symbol, default: USD)
        market_data_subscription_type: Type of market data subscription ("realtime" or "delayed").

    Returns:
        List of tickers for the given contract IDs.

    """
    try:
      await self._connect()
      if contract_ids is None:
        # Create contract from symbol details
        contracts = [Contract(symbol = symbol, secType = sec_type, exchange = exchange, currency = currency)]
      else:
        contracts = [Contract(conId=contract_id) for contract_id in contract_ids]
        
      qualified_contracts = await asyncio.wait_for(
        self.ib.qualifyContractsAsync(*contracts),
          timeout=self.config.ib_request_timeout,
        )
      
      if qualified_contracts is None or len( qualified_contracts) == 0:
        raise Exception( "No qualified contracts found")

      # Determine market data type based on subscription type
      if market_data_subscription_type.lower() == "realtime":
        market_data_type = LIVE
      else:
        market_data_type = DELAYED
      self.ib.reqMarketDataType(market_data_type)
      
      # Request streaming data for all qualified contracts
      # Generic ticks: 221=mark price, 165=52-week high/low, 106=opt implied vol, 104=hist vol, 100=opt volume, 101=opt open interest
      generic_tick_list = "221,165,106,104,100,101"
      tickers = [self.ib.reqMktData(contract, genericTickList=generic_tick_list) for contract in qualified_contracts]

      try:
          # Wait until all tickers have data and have stabilized (no changes for 2 cycles)
          timeout = self.config.ib_request_timeout
          interval = 0.5
          loop = asyncio.get_event_loop()
          start = loop.time()
          
          def _get_ticker_snapshot(ticker):
              """Get a snapshot of all comparable fields for change detection."""
              return self._get_ticker_fields(ticker)
          
          # Track consecutive cycles with no changes
          stable_cycles = 0
          prev_snapshot = None
          ready = False
          
          while not ready:
              await asyncio.sleep(interval)
              
              # Check if all tickers have time
              all_have_time = all(ticker.time is not None for ticker in tickers)
              
              if all_have_time:
                  # Check for changes since last iteration
                  curr_snapshot = tuple(_get_ticker_snapshot(t) for t in tickers)
                  
                  if prev_snapshot is not None and curr_snapshot == prev_snapshot:
                      stable_cycles += 1
                  else:
                      stable_cycles = 0  # Reset if data changed
                  
                  prev_snapshot = curr_snapshot
                  
                  # Ready if data is stable for 2 consecutive cycles
                  if stable_cycles >= 2:
                      ready = True
              else:
                  # Reset stability tracking if any ticker loses time
                  stable_cycles = 0
                  prev_snapshot = None
              
              # Check timeout
              elapsed = loop.time() - start
              if elapsed >= timeout:
                  logger.warning(f"Timeout waiting for market data after {elapsed:.1f}s for {len(tickers)} tickers")
                  # Still proceed if we have data, even if not fully stable
                  if all_have_time:
                      logger.info(f"Proceeding with {len(tickers)} tickers despite timeout")
                      ready = True
                  else:
                      break

          # Process tickers
          if ready:
            result = self._process_tickers(tickers)

      finally:
          # Cancel all streaming subscriptions
          for contract in qualified_contracts:
              self.ib.cancelMktData(contract)

          # Optionally clear tickers list if you no longer need it
          tickers.clear()

      # # Check if we got any greeks data (only for options contracts)
      # options_contracts = [ticker for ticker in result if ticker.sec_type == "OPT"]
      # has_greeks = False
      # if options_contracts:
      #   has_greeks = any(ticker.greeks for ticker in options_contracts)

      # # Only restart if we have options contracts but no greeks data
      # if options_contracts and not has_greeks:
      #   logger.warning("No greeks data for options contracts, restarting gateway...")
      #   await self.send_command_to_ibc("RESTART")
      #   await asyncio.sleep(30)
      #   await self._connect()

      #   # Second attempt
      #   if self._is_market_open():
      #     self.ib.reqMarketDataType(LIVE)
      #   else:
      #     self.ib.reqMarketDataType(DELAYED)
      #   tickers = await self.ib.reqTickersAsync(*qualified_contracts)

      #   # Process tickers again
      #   result = self._process_tickers(tickers)
      #   # Check if we got greeks data after restart (only for options)
      #   options_contracts = [ticker for ticker in result if ticker.sec_type == "OPT"]
      #   has_greeks = False
      #   if options_contracts:
      #     has_greeks = any(ticker.greeks for ticker in options_contracts)
      #   if options_contracts and not has_greeks:
      #     logger.warning("Still no greeks data after gateway restart")

      result_dict = [ticker.model_dump() for ticker in result]

    except Exception as e:
      logger.error("Error getting tickers: {}", str(e))
      raise
    else:
      return result_dict

  async def get_and_filter_options(
      self,
      underlying_symbol: str,
      underlying_sec_type: str,
      underlying_con_id: int,
      filters: dict | None = None,
      criteria: dict | None = None,
    ) -> list[dict]:
    """Get and filter option chain based on market data criteria.

    Args:
      underlying_symbol: Symbol of the underlying contract.
      underlying_sec_type: Security type of the underlying contract.
      underlying_con_id: ConID of the underlying contract.
      filters: Dictionary of filters to apply to the options chain,
      you must specify at least one filter to reduce the number of options in the chain,
      you must specify expirations, you can specify tradingClass, strikes, and rights.
        - tradingClass: List of trading classes to filter by.
        - expirations: List of expirations to filter by.
        - strikes: List of strikes to filter by.
        - rights: List of rights to filter by.
      criteria: Dictionary of criteria to match:
        - min_delta: Minimum delta value (float)
        - max_delta: Maximum delta value (float)

    Returns:
      List of dictionaries containing filtered option details and market data

    """
    try:
      await self._connect()  # Connect once for both operations

      # Get options chain
      options_chain = await self.contract_client.get_options_chain(
        underlying_symbol,
        underlying_sec_type,
        underlying_con_id,
        filters,
      )
      options_chain_df = pd.DataFrame(options_chain)

      # Get market data for all options
      market_data = await self.get_tickers(
        symbol=underlying_symbol,
        sec_type=underlying_sec_type,
        exchange="",
        currency="",
        contract_ids=options_chain_df["conId"].tolist()
      )

      if not market_data:
        logger.warning("No market data available for options")
        return []

      # Convert to DataFrame for filtering
      market_data_df = pd.DataFrame(market_data)

      # Apply criteria filters
      filtered_data = market_data_df.copy()

      # Apply delta range if specified
      if criteria and ("min_delta" in criteria or "max_delta" in criteria):
        # Filter out rows with missing greeks data first
        filtered_data = filtered_data[
          filtered_data["greeks"].apply(
            lambda x: bool(x and x.get("delta") is not None),
          )
        ]

        # Apply delta filters
        filtered_data = filtered_data[
          filtered_data["greeks"].apply(
            lambda x: (
              ("min_delta" not in criteria or
                x["delta"] >= criteria["min_delta"]) and
              ("max_delta" not in criteria or
                x["delta"] <= criteria["max_delta"])
            ),
          )
        ]

      if filtered_data.empty:
        logger.warning("No options found matching the criteria")
        return []

      # Convert filtered DataFrame to list of Pydantic models
      filtered_tickers = []
      for _, row in filtered_data.iterrows():
        ticker_kwargs = {
          "contract_id": row["contract_id"],
          "symbol": row["symbol"],
          "sec_type": row["sec_type"],
          "last": row["last"] if pd.notna(row["last"]) else None,
          "close": row["close"] if pd.notna(row["close"]) else None,
          "bid": row["bid"] if pd.notna(row["bid"]) else None,
          "ask": row["ask"] if pd.notna(row["ask"]) else None,
          "bid_size": row["bid_size"] if pd.notna(row.get("bid_size")) else None,
          "ask_size": row["ask_size"] if pd.notna(row.get("ask_size")) else None,
          "high": row["high"] if pd.notna(row["high"]) else None,
          "low": row["low"] if pd.notna(row["low"]) else None,
          "volume": row["volume"] if pd.notna(row["volume"]) else None,
          "mark": row["mark"] if pd.notna(row.get("mark")) else None,
          "high_52_week": row["high_52_week"] if pd.notna(row.get("high_52_week")) else None,
          "low_52_week": row["low_52_week"] if pd.notna(row.get("low_52_week")) else None,
          "option_volume": row["option_volume"] if pd.notna(row.get("option_volume")) else None,
          "option_open_interest": row["option_open_interest"] if pd.notna(row.get("option_open_interest")) else None,
          "greeks": row["greeks"],
        }
        # Only add timestamp if it exists and is not None
        if pd.notna(row.get("timestamp")):
          ticker_kwargs["timestamp"] = row["timestamp"]
        # Only add market_data_type if it exists and is not None
        if pd.notna(row.get("market_data_type")):
          ticker_kwargs["market_data_type"] = row["market_data_type"]
        ticker_data = MarketData(**ticker_kwargs)
        filtered_tickers.append(ticker_data)

      # Return as list of dictionaries
      return [ticker.model_dump() for ticker in filtered_tickers]

    except Exception as e:
      logger.error("Error filtering options: {}", str(e))
      raise

  async def get_historical_data(
      self,
      symbol: str | None = None,
      contract_id: int | None = None,
      sec_type: str = "STK",
      exchange: str = "SMART",
      currency: str = "USD",
      duration: str = "1 D",
      bar_size: str = "1 min",
      what_to_show: str = "TRADES",
      use_rth: bool = True,
      end_date: str | None = None
    ) -> list[BarData]:
    """Get historical market data.
    
    Args:
      symbol: Symbol to get data for (optional if contract_id is provided)
      contract_id: Contract ID to get data for (optional if symbol is provided).
        Use this for better performance as it avoids symbol lookup.
      sec_type: Security type (default: STK) - used with symbol
      exchange: Exchange (default: SMART) - used with symbol
      currency: Currency (default: USD)
      duration: Duration string (e.g., '1 D', '1 W', '1 M')
      bar_size: Bar size (e.g., '1 min', '5 mins', '1 hour', '1 day')
      what_to_show: What to show (TRADES, MIDPOINT, BID, ASK)
      use_rth: Use regular trading hours only
      end_date: End date/time for historical data (default: '' = now).
        Supported formats:
        - Date only: 'YYYYMMDD' (e.g., '20260223') - will be converted to 'YYYYMMDD HH:MM:SS {timezone}' using the contract's liquidHours
        - Date with time: 'YYYYMMDD HH:MM:SS' (e.g., '20260223 15:30:00')
        - Date with time and timezone: 'YYYYMMDD HH:MM:SS Timezone' (e.g., '20260223 15:30:00 US/Eastern')
        
      Note:
        When using date-only format, the closing time is determined from the contract's
        liquidHours field. If liquidHours is not available, defaults to 15:59:00 US/Eastern.
        
    Note:
      Either 'symbol' or 'contract_id' must be provided, but not both.
      Using 'contract_id' is recommended as it's more efficient.
      
    Returns:
      List of historical bar data
      
    Raises:
      Exception: If contract qualification fails or historical data cannot be retrieved
    """
    await self._connect()
    
    try:
      # Create contract - either from contract_id or from symbol details
      if contract_id:
        # Use contract ID directly
        ib_contract = Contract(conId=contract_id)
        logger.debug(f"Creating contract from contract_id: {contract_id}")
      else:
        # Create contract from symbol details
        ib_contract = Contract()
        ib_contract.symbol = symbol.upper()  # Ensure symbol is uppercase
        ib_contract.secType = sec_type.upper()  # Ensure security type is uppercase
        ib_contract.exchange = exchange.upper()  # Ensure exchange is uppercase
        ib_contract.currency = currency.upper()  # Ensure currency is uppercase
        logger.debug(f"Creating contract from symbol: {symbol}")
      
      logger.debug(f"Qualifying contract: {ib_contract}")
      
      # Qualify contract
      try:
        qualified_contracts = await asyncio.wait_for(
          self.ib.qualifyContractsAsync(ib_contract),
          timeout=self.config.ib_request_timeout,
        )
        if not qualified_contracts or not qualified_contracts[0]:
          if contract_id:
            raise ValueError(f"No contract found for contract_id {contract_id}")
          else:
            raise ValueError(f"No contract found for {symbol} (type: {sec_type}, exchange: {exchange}, currency: {currency})")
        
        ib_contract = qualified_contracts[0]
        logger.debug(f"Qualified contract: {ib_contract}")
        
        # Get timezone and liquid hours for the contract
        contract_timezone = None
        liquid_hours = None
        if end_date:
          try:
            contract_details = await self.ib.reqContractDetailsAsync(ib_contract)
            if contract_details and contract_details[0]:
              contract_timezone = contract_details[0].timeZoneId
              liquid_hours = contract_details[0].liquidHours
              logger.debug(f"Contract timezone: {contract_timezone}, liquidHours: {liquid_hours}")
          except Exception as tz_error:
            logger.warning(f"Could not get contract timezone: {tz_error}")
        
      except Exception as qual_error:
        if contract_id:
          error_msg = f"Failed to qualify contract with ID {contract_id}: {str(qual_error)}"
        else:
          error_msg = f"Failed to qualify contract {symbol} (type: {sec_type}, exchange: {exchange}): {str(qual_error)}"
        logger.error(error_msg)
        raise ValueError(error_msg) from qual_error
      
      try:
        # Request historical data
        logger.debug(f"Requesting historical data for {ib_contract.symbol} ({ib_contract.secType})...")
        
        # Format end_date with timezone if provided
        if end_date:
          # If end_date already has time component (space or dash), use as-is
          if ' ' in end_date or '-' in end_date:
            end_date_time = end_date
          else:
            # Add time and timezone - get closing time from liquidHours
            close_time = self._get_session_close(liquid_hours, end_date) if liquid_hours else None
            
            if close_time:
              # Format: HHMM -> HH:MM:SS
              if len(close_time) == 4:
                close_time = f"{close_time[:2]}:{close_time[2:]}:00"
              if contract_timezone:
                end_date_time = f"{end_date} {close_time} {contract_timezone}"
              else:
                end_date_time = f"{end_date} {close_time} US/Eastern"
            else:
              # Fallback to default close time if liquidHours not available
              if contract_timezone:
                end_date_time = f"{end_date} 15:59:00 {contract_timezone}"
              else:
                end_date_time = f"{end_date} 15:59:00 US/Eastern"
        else:
          end_date_time = ''
        
        logger.info(f"Historical request: endDateTime='{end_date_time}', durationStr='{duration}', barSizeSetting='{bar_size}'")
        
        bars = await self.ib.reqHistoricalDataAsync(
          contract=ib_contract,
          endDateTime=end_date_time,
          durationStr=duration,
          barSizeSetting=bar_size,
          whatToShow=what_to_show,
          useRTH=use_rth,
          timeout=self.config.ib_request_timeout
        )
        
        if not bars:
          logger.warning(f"No historical data returned for {ib_contract.symbol} (type: {ib_contract.secType})")
          return []
        
        logger.debug(f"Received {len(bars)} bars of historical data for {ib_contract.symbol}")
        
        return [
          BarData(
            date=bar.date.isoformat() if hasattr(bar.date, 'isoformat') else str(bar.date),
            open=float(bar.open) if bar.open is not None else None,
            high=float(bar.high) if bar.high is not None else None,
            low=float(bar.low) if bar.low is not None else None,
            close=float(bar.close) if bar.close is not None else None,
            volume=int(bar.volume) if bar.volume is not None else 0,
            wap=float(bar.wap) if hasattr(bar, 'wap') and bar.wap is not None else None,
            count=int(bar.barCount) if hasattr(bar, 'barCount') and bar.barCount is not None else None
          )
          for bar in bars
        ]
        
      except Exception as hist_error:
        error_msg = f"Failed to get historical data for {ib_contract.symbol} (type: {ib_contract.secType}): {str(hist_error)}"
        logger.error(error_msg)
        raise Exception(error_msg) from hist_error
      
    except Exception as e:
      logger.error(f"Historical data error for symbol={symbol}, contract_id={contract_id}: {str(e)}", exc_info=True)
      raise Exception(f"Historical data error: {str(e)}")

