import ccxt
import pandas as pd
import pytz
from datetime import datetime, timedelta, time
from config import SYMBOLS, TIMEFRAMES, SESSION_START, SESSION_END
import logging

logger = logging.getLogger(__name__)

class DataHandler:
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
        self.timezone = pytz.timezone('US/Eastern')
        self.buffers = {symbol: {tf: pd.DataFrame() for tf in TIMEFRAMES} for symbol in SYMBOLS}
        self.last_update = {symbol: None for symbol in SYMBOLS}

    def fetch_ohlcv(self, symbol, timeframe, limit=500):
        """Fetch OHLCV data from Alpaca via CCXT."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv:
                logger.warning(f"No data returned for {symbol} {timeframe}")
                return pd.DataFrame()
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error fetching {symbol} {timeframe}: {e}")
            return pd.DataFrame()

    def update_buffers(self):
        """Fetch latest 1m candles and resample to higher timeframes."""
        now = datetime.now(self.timezone)
        for symbol in SYMBOLS:
            # Fetch recent 1m candles (last 2 days to ensure we have enough for resampling)
            df_1m = self.fetch_ohlcv(symbol, '1m', limit=500)
            if df_1m.empty:
                logger.warning(f"No 1m data for {symbol}")
                continue
            # Keep only recent data to avoid excessive memory
            cutoff = now - timedelta(days=2)
            df_1m = df_1m[df_1m.index >= cutoff]
            self.buffers[symbol]['1m'] = df_1m

            # Resample to higher timeframes
            for tf_name, tf_minutes in TIMEFRAMES.items():
                if tf_name == '1m':
                    continue
                # Resample rule: e.g., '5min', '15min', etc.
                rule = f'{tf_minutes}min'
                try:
                    df_resampled = df_1m.resample(rule).agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    }).dropna()
                    self.buffers[symbol][tf_name] = df_resampled
                except Exception as e:
                    logger.error(f"Error resampling {symbol} to {tf_name}: {e}")

    def get_latest(self, symbol, timeframe, n=1):
        """Return the last n rows for the given symbol and timeframe."""
        df = self.buffers.get(symbol, {}).get(timeframe)
        if df is None or df.empty:
            return pd.DataFrame()
        return df.tail(n)

    def is_market_open(self):
        """Check if current time is within NY session (EST)."""
        now = datetime.now(self.timezone)
        current_time = now.time()
        start = time.fromisoformat(SESSION_START)
        end = time.fromisoformat(SESSION_END)
        return start <= current_time <= end