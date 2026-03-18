# ICT + SMC Trading Bot

A rule-based trading bot implementing the Inner Circle Trader (ICT) and Smart Money Concepts (SMC) methodology for scalping the NY market open on ES and NQ futures via Alpaca (paper/live).

## Features
- Higher timeframe bias filter (Daily HH/HL or LH/LL)
- Liquidity sweep detection (wick beyond recent swing high/low)
- Displacement strength filter
- Market Structure Shift (MSS) confirmation (CHOCH then BOS)
- Confluence: Order Block (OB) prioritized over Fair Value Gap (FVG)
- Lower timeframe trigger (CHOCH/BOS on 1m)
- Stop loss beyond sweep level (matched to OB timeframe)
- Take profit at next liquidity pool or 1:2 risk-reward (placeholder)
- Position sizing based on risk % and stop distance
- Session filter: NY market open 09:30–12:50 EST
- Daily loss cap and max trades per day
- CSV trade journal for manual review
- Dry-run mode (simulate orders) for safe testing

## Setup

1. **Clone or copy this folder** to your machine.

2. **Install Python 3.9+** if not already installed.

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Obtain Alpaca API keys**:
   - Sign up at [https://alpaca.markets](https://alpaca.markets)
   - Enable paper trading
   - Go to API Keys → generate a Key ID and Secret Key
   - Copy them into the next step.

5. **Configure your environment**:
   ```bash
   cp .env.example .env
   # Edit .env and replace the placeholders with your actual keys
   ```
   The `.env` file is git‑ignored and never committed.

6. **(Optional) Test the connection**:
   ```bash
   python -c "import config; print('Key loaded:', bool(config.APACA_API_KEY))"
   ```

7. **Run the bot**:
   ```bash
   python main.py
   ```
   The bot will start in **dry‑run mode** (`DRY_RUN = True` in `config.py`). It will:
   - Fetch live 1‑minute bars from Alpaca via CCXT
   - Compute higher timeframes (5m, 15m, 30m, 1h, 4h, 1d) on the fly
   - Evaluate the ICT+SMC strategy each minute
   - Print any signals to the console
   - Log simulated trades to `trades.csv` (journal)

8. **When you're ready to trade with real paper funds**:
   - Open `config.py`
   - Set `DRY_RUN = False`
   - Restart the bot
   - The bot will now place **market orders** via your Alpaca paper account.
   - **Important**: You will still need to manage the position (monitor fills, update stop loss, take profit, close the trade) and then log the final outcome to the journal.  
     This skeleton logs the trade at signal time with P&L=0; you should update the journal manually after each trade closes, or extend the `executor.py` to handle order fills, SL/TP OCO orders, and trade closing.

## Files

- `config.py` – All parameters: symbols, risk, session times, caps, etc.
- `data_handler.py` – CCXT Alpaca wrapper; fetches and resamples candles.
- `strategy.py` – Core ICT+SMC logic (sweep → displacement → MSS → OB/FVG → LTF trigger → SL/TP).
- `executor.py` – Places orders via CCXT (dry‑run or live).
- `risk_manager.py` – Tracks daily P&L, trade count, kill switch.
- `logger.py` – Simple CSV journal.
- `main.py` – Event loop: updates data, checks for signal, executes/logs.

## Customization

- **Change instruments**: Edit `SYMBOLS` in `config.py` (e.g., `["MES", "MNQ"]` for micros).
- **Adjust risk**: Modify `RISK_PER_TRADE`, `DAILY_LOSS_CAP`, `MAX_TRADES_PER_DAY`.
- **Change session**: Edit `SESSION_START` and `SESSION_END`.
- **Add news filter**: Replace `is_news_blackout()` in `strategy.py` with a real news API call.
- **Improve TP logic**: Replace the placeholder 1:2 RR in `calculate_sl_tp` with actual liquidity pool detection or StdDev/Fib extensions.
- **Add position management**: Extend `executor.py` to monitor open orders, attach OCO SL/TP orders, and log final P&L.

## Safety

- The bot will never trade outside the NY session (09:30–12:50 EST).
- Daily loss cap and max trades per day are enforced.
- Set `DRY_RUN = True` while testing to avoid sending real orders.
- A kill switch can be activated by creating an empty file named `killswitch.txt` in the bot folder.

## Next Steps

1. Run in dry‑run mode for at least 24–48 hours to see how often signals fire and whether they look reasonable.
2. Examine `trades.csv` and note any patterns (e.g., many signals in choppy markets).
3. Tune the strategy (e.g., increase `MIN_DISP_STRENGTH`, require stronger displacement, add volume filter).
4. When confident, set `DRY_RUN = False` and trade with small size in your Alpaca paper account.
5. Journal each trade’s outcome (win/loss, emotion) in the `trades.csv` file.
6. Review weekly and adjust parameters as needed.

## Disclaimer

This bot is for educational and paper‑trading purposes only. Trading futures involves substantial risk and is not suitable for everyone. Past performance is not indicative of future results. Use at your own risk. The author is not liable for any losses incurred.
