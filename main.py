import time
import pandas as pd
from config import *
from data_handler import DataHandler
from strategy import generate_signal
from executor import Executor
from risk_manager import RiskManager
from logger import TradeLogger

def main():
    print("Starting ICT+SMC Trading Bot...")
    print(f"Symbols: {SYMBOLS}")
    print(f"Risk per trade: {RISK_PER_TRADE*100}%")
    print(f"Daily loss cap: ${DAILY_LOSS_CAP}")
    print(f"Max trades per day: {MAX_TRADES_PER_DAY}")
    print(f"Trading window: {SESSION_START} - {SESSION_END} EST")
    print(f"Dry run mode: {DRY_RUN}")
    print("-" * 50)

    data_handler = DataHandler()
    executor = Executor()
    risk_manager = RiskManager()
    logger = TradeLogger()

    try:
        while True:
            # Wait until the next minute starts (to avoid fetching same bar multiple times)
            now = pd.Timestamp.now(tz='US/Eastern')
            seconds_to_next_minute = 60 - now.second - now.microsecond/1_000_000
            if seconds_to_next_minute > 0:
                time.sleep(seconds_to_next_minute)

            # Update data buffers (fetch latest candles)
            data_handler.update_buffers()

            # Check if we can trade (risk limits, session, etc.)
            if not risk_manager.can_trade():
                if risk_manager.get_daily_pnl() <= -DAILY_LOSS_CAP:
                    print(f"[{now}] Daily loss cap reached. Pausing trading for the day.")
                elif risk_manager.get_trades_today() >= MAX_TRADES_PER_DAY:
                    print(f"[{now}] Max trades per day reached. Pausing trading for the day.")
                # In dry run, we still allow signals to be generated but not sent.
                # We'll continue to let the strategy run for logging purposes.
                # Optionally, we could break or sleep longer.

            # Generate signal
            signal = generate_signal(data_handler)
            if signal is not None:
                symbol = signal['symbol']
                side = 'buy' if signal['direction'] == 'long' else 'sell'
                qty = signal['quantity']
                entry = signal['entry_price']
                sl = signal['sl_price']
                tp = signal['tp_price']
                reason = signal['reason']
                timestamp = signal['timestamp']

                print(f"[{now}] SIGNAL: {side.upper()} {qty:.4f} {symbol} @ {entry:.2f}")
                print(f"  SL: {sl:.2f} | TP: {tp:.2f} | Reason: {reason}")

                if DRY_RUN:
                    # In dry run, we simulate a fill at the entry price (or we could wait for next tick)
                    # For simplicity, we log the trade immediately with a simulated outcome.
                    # In reality, you would want to wait for the order to fill, then update SL/TP, then monitor.
                    # Here we just log as a placeholder; you can replace with actual order handling.
                    pnl = 0.0  # unknown until trade closes
                    emotion = ""  # to be filled by you later via journal edit
                    executor.log_trade(timestamp, symbol, side, entry, sl, tp, qty, pnl, reason, emotion)
                    print(f"  [DRY RUN] Logged trade to journal.")
                else:
                    # Place real order (market order at entry price)
                    order = executor.place_order(symbol, side, qty, price=entry)
                    if order is not None:
                        # In a real bot, you would now:
                        # 1. Wait for the order to fill (check order status)
                        # 2. Once filled, monitor the position and update SL/OCO orders
                        # 3. When position closes, calculate P&L and log to journal
                        # For this skeleton, we'll just log the intent and leave position management to you.
                        print(f"  Order placed. You will need to manage position and update journal on close.")
                    else:
                        print(f"  Failed to place order.")
            else:
                # No signal this minute
                pass

            # Optional: print status every 10 minutes
            if now.minute % 10 == 0 and now.second == 0:
                print(f"[{now}] Status - Daily P&L: ${risk_manager.get_daily_pnl():.2f}, Trades today: {risk_manager.get_trades_today()}")

    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"\nError in main loop: {e}")
        raise

if __name__ == "__main__":
    main()