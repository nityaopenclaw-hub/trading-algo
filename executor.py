import ccxt
from config import DRY_RUN
from logger import TradeLogger
import logging

logger = logging.getLogger(__name__)

class Executor:
    def __init__(self):
        self.exchange = ccxt.alpaca({
            'apiKey': config.ALPACA_API_KEY,
            'secret': config.ALPACA_API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
            },
            'urls': {
                'api': {
                    'rest': 'https://paper-api.alpaca.markets',
                }
            }
        })
        self.logger = TradeLogger()

    def place_order(self, symbol, side, quantity, price=None):
        """
        Place an order via Alpaca.
        If DRY_RUN is True, only log the intended order.
        side: 'buy' or 'sell'
        quantity: amount (contracts)
        price: price for limit order; if None, market order.
        Returns order dict if successful, None otherwise.
        """
        if quantity <= 0:
            logger.warning(f"Attempted to place order with non-positive quantity: {quantity}")
            return None
            
        if DRY_RUN:
            order_type = 'limit' if price is not None else 'market'
            logger.info(f"[DRY RUN] Would place {order_type} {side} order for {quantity} {symbol} at {price if price else 'market'}")
            return None
        try:
            params = {}
            if price is not None:
                order = self.exchange.create_limit_order(symbol, side, quantity, price, params)
            else:
                order = self.exchange.create_market_order(symbol, side, quantity, params)
            logger.info(f"Order placed: {order['id']} {side} {quantity} {symbol}")
            return order
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def log_trade(self, timestamp, symbol, side, entry, sl, tp, qty, pnl, reason, emotion=""):
        self.logger.log_trade(timestamp, symbol, side, entry, sl, tp, qty, pnl, reason, emotion)