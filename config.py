import os
from dotenv import load_dotenv

load_dotenv()  # loads .env file

# Alpaca API credentials
APACA_API_KEY = os.getenv("APACA_API_KEY")
APACA_API_SECRET = os.getenv("APACA_API_SECRET")

# Trading symbols
SYMBOLS = ["ES", "NQ"]  # E-mini S&P 500 and E-mini NASDAQ 100 futures on Alpaca

# Timeframes (in minutes) - we will fetch 1m and resample upward
TIMEFRAMES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440
}

# Trading window (NY market open, EST)
SESSION_START = "09:30"
SESSION_END = "12:50"

# Risk management
RISK_PER_TRADE = 0.02         # 2% of equity per trade
DAILY_LOSS_CAP = 5000.0       # halt trading if daily P&L <= -$5000
MAX_TRADES_PER_DAY = 3        # maximum number of trades per day

# Slippage and order type
ORDER_TYPE = "market"         # or "limit" if you prefer
SLIPPAGE_TOLERANCE = 0.0      # for market orders, set to 0; for limit, adjust

# Take profit method: "next_liquidity" or "stddev_fib"
TP_METHOD = "next_liquidity"  # could also be "stddev_fib"

# Standard deviation multiplier for TP (if using stddev_fib)
TP_STDDEV_MULT = 2.0          # 2 standard deviations from mean of displacement move
TP_FIB_LEVELS = [1.27, 1.62]  # Fibonacci extension levels

# Minimum displacement candle strength (as % of candle range)
MIN_DISP_STRENGTH = 0.6       # displacement candle body must be at least 60% of its range

# Sweep detection: how far back to look for recent swing high/low
SWEEP_LOOKBACK = 20           # number of candles to consider for swing point

# Kill switch file: if this file exists, bot stops
KILL_SWITCH_FILE = "killswitch.txt"

# Dry run mode: set False to send real orders (paper trading on Alpaca)
DRY_RUN = True