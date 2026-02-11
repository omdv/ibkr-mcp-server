"""Trading operations service."""
import asyncio
from ib_async import Contract as IBContract, Order as IBOrder, Stock, Option, Future, Forex
from app.services.client import IBClient
from app.core.setup_logging import logger
from app.models import (
  ContractRequest, OrderRequest, OrderResponse, OpenOrder, SecType
)


class TradingClient(IBClient):
  """Trading operations."""

  def _contract_to_ib(self, contract: ContractRequest) -> IBContract:
    """Convert ContractRequest to IB Contract."""
    if contract.sec_type == SecType.STOCK:
      return Stock(
        symbol=contract.symbol,
        exchange=contract.exchange,
        currency=contract.currency
      )
    elif contract.sec_type == SecType.OPTION:
      return Option(
        symbol=contract.symbol,
        lastTradeDateOrContractMonth=contract.expiry or '',
        strike=float(contract.strike or 0),
        right=contract.right or 'C',
        exchange=contract.exchange,
        currency=contract.currency
      )
    elif contract.sec_type == SecType.FUTURE:
      return Future(
        symbol=contract.symbol,
        lastTradeDateOrContractMonth=contract.last_trade_date or '',
        exchange=contract.exchange,
        currency=contract.currency
      )
    elif contract.sec_type == SecType.FOREX:
      return Forex(
        pair=contract.symbol,
        exchange=contract.exchange,
        currency=contract.currency
      )
    else:
      # Fallback to generic contract
      ib_contract = IBContract()
      ib_contract.symbol = contract.symbol
      ib_contract.secType = contract.sec_type.value
      ib_contract.exchange = contract.exchange
      ib_contract.currency = contract.currency
      if contract.local_symbol:
        ib_contract.localSymbol = contract.local_symbol
      if contract.con_id:
        ib_contract.conId = contract.con_id
      return ib_contract

  def _order_to_ib(self, order: OrderRequest) -> IBOrder:
    """Convert OrderRequest to IB Order."""
    ib_order = IBOrder()
    ib_order.action = order.action.value
    ib_order.totalQuantity = float(order.total_quantity)
    ib_order.orderType = order.order_type.value
    ib_order.tif = order.time_in_force.value
    ib_order.outsideRth = order.outside_rth
    ib_order.hidden = order.hidden
    
    if order.lmt_price:
      ib_order.lmtPrice = float(order.lmt_price)
    if order.aux_price:
      ib_order.auxPrice = float(order.aux_price)
    if order.good_after_time:
      ib_order.goodAfterTime = order.good_after_time
    if order.good_till_date:
      ib_order.goodTillDate = order.good_till_date
    
    return ib_order

  async def place_order(
    self,
    contract: ContractRequest,
    order: OrderRequest
  ) -> OrderResponse:
    """Place an order.
    
    Args:
      contract: Contract to trade
      order: Order details
      
    Returns:
      Order response with order ID and status
    """
    await self._connect()
    
    try:
      ib_contract = self._contract_to_ib(contract)
      ib_order = self._order_to_ib(order)
      
      # Qualify contract if needed
      qualified_contracts = await asyncio.wait_for(
          self.ib.qualifyContractsAsync(ib_contract),
          timeout=self.config.ib_request_timeout,
        )
      if not qualified_contracts:
        raise Exception(f"Could not qualify contract: {contract.symbol}")
      
      ib_contract = qualified_contracts[0]
      
      # Place order
      trade = self.ib.placeOrder(ib_contract, ib_order)
      await asyncio.sleep(0.5)  # Wait for order to be acknowledged
      
      logger.info(f"Order placed: {trade.order.orderId} for {contract.symbol}")
      
      return OrderResponse(
        order_id=trade.order.orderId,
        status=trade.orderStatus.status,
        symbol=contract.symbol,
        action=order.action.value,
        quantity=float(order.total_quantity),
        filled=float(trade.orderStatus.filled),
        remaining=float(trade.orderStatus.remaining),
        avg_fill_price=float(trade.orderStatus.avgFillPrice) if trade.orderStatus.avgFillPrice else None
      )
      
    except Exception as e:
      logger.error(f"Failed to place order: {e}")
      raise Exception(f"Order placement error: {e}")

  async def cancel_order(self, order_id: int) -> bool:
    """Cancel an order.
    
    Args:
      order_id: Order ID to cancel
      
    Returns:
      True if cancellation was successful
    """
    await self._connect()
    
    try:
      # Get all open trades to find the order
      open_trades = self.ib.openTrades()
      
      # Find matching order
      target_order = None
      for trade in open_trades:
        if trade.order.orderId == order_id:
          target_order = trade.order
          break
      
      if target_order is None:
        logger.error(f"Order with ID {order_id} not found in open trades")
        raise Exception(f"Order {order_id} not found")
      
      # Cancel the order
      self.ib.cancelOrder(target_order)
      logger.info(f"Order cancelled: {order_id}")
      return True
      
    except Exception as e:
      logger.error(f"Failed to cancel order {order_id}: {e}")
      raise Exception(f"Order cancellation error: {e}")

  async def get_open_orders(self) -> list[OpenOrder]:
    """Get all open orders.
    
    Returns:
      List of open orders
    """
    await self._connect()
    
    try:
      await asyncio.wait_for(
          self.ib.reqOpenOrdersAsync(),
          timeout=self.config.ib_request_timeout,
        )
      trades = self.ib.openTrades()
      
      orders_data = []
      for trade in trades:
        orders_data.append(OpenOrder(
          order_id=trade.order.orderId,
          symbol=trade.contract.symbol,
          sec_type=trade.contract.secType,
          action=trade.order.action,
          quantity=float(trade.order.totalQuantity),
          order_type=trade.order.orderType,
          status=trade.orderStatus.status,
          limit_price=float(trade.order.lmtPrice) if trade.order.lmtPrice else None,
          aux_price=float(trade.order.auxPrice) if trade.order.auxPrice else None,
          filled=float(trade.orderStatus.filled),
          remaining=float(trade.orderStatus.remaining),
          avg_fill_price=float(trade.orderStatus.avgFillPrice) if trade.orderStatus.avgFillPrice else None
        ))
      
      return orders_data
    except Exception as e:
      logger.error(f"Failed to get open orders: {e}")
      raise Exception(f"Open orders error: {e}")
