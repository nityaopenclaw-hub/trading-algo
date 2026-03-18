import pandas as pd
import numpy as np
from config import *

def is_news_blackout():
    """
    Placeholder for news filter.
    In the future, integrate with a news API (e.g., Forex Factory, Benzinga, etc.)
    For now, always return False (no blackout).
    """
    return False

def get_htf_bias(df_daily):
    """
    Determine higher timeframe bias from daily candles.
    Returns 'up' if HH/HL, 'down' if LH/LL, else None.
    """
    if len(df_daily) < 2:
        return None
    # Use last two daily candles to check for higher high/low or lower high/low
    # For simplicity, we consider the last completed daily candle (index -2) and previous (-3)
    if len(df_daily) >= 3:
        c1 = df_daily.iloc[-3]  # day before yesterday
        c2 = df_daily.iloc[-2]  # yesterday
        # Up trend: higher high and higher low
        if c2['high'] > c1['high'] and c2['low'] > c1['low']:
            return 'up'
        # Down trend: lower high and lower low
        if c2['high'] < c1['high'] and c2['low'] < c1['low']:
            return 'down'
    return None

def detect_swing_points(df, lookback=SWEEP_LOOKBACK):
    """
    Identify recent swing high and swing low within lookback period.
    Returns (swing_high_price, swing_low_price, swing_high_idx, swing_low_idx)
    """
    if len(df) < lookback:
        return None, None, None, None
    recent = df.iloc[-lookback:]
    swing_high_idx = recent['high'].idxmax()
    swing_low_idx = recent['low'].idxmin()
    swing_high_price = recent.loc[swing_high_idx, 'high']
    swing_low_price = recent.loc[swing_low_idx, 'low']
    return swing_high_price, swing_low_price, swing_high_idx, swing_low_idx

def detect_sweep(df_1m):
    """
    Detect a liquidity sweep: price wicks beyond recent swing high or low.
    Returns dict with details if sweep found, else None.
    """
    if len(df_1m) < SWEEP_LOOKBACK + 2:
        return None
    # Use the candle before the most recent to define the swing points (to avoid using the forming candle)
    df_recent = df_1m.iloc[-(SWEEP_LOOKBACK+1):-1]  # exclude the last forming candle
    swing_high_price, swing_low_price, _, _ = detect_swing_points(df_recent, lookback=SWEEP_LOOKBACK)
    if swing_high_price is None or swing_low_price is None:
        return None
    last = df_1m.iloc[-1]  # most recent candle
    # Check if wick goes above swing high or below swing low
    swept_high = last['high'] > swing_high_price
    swept_low = last['low'] < swing_low_price
    if not (swept_high or swept_low):
        return None
    # Determine direction of sweep
    if swept_high:
        sweep_type = 'high'
        sweep_level = swing_high_price
        # After sweeping high, we expect a bearish displacement
        expected_displacement = 'down'
    else:
        sweep_type = 'low'
        sweep_level = swing_low_price
        expected_displacement = 'up'
    return {
        'type': sweep_type,
        'level': sweep_level,
        'swept_high': swept_high,
        'swept_low': swept_low,
        'expected_displacement': expected_displacement,
        'timestamp': last.name,
        'high': last['high'],
        'low': last['low'],
        'close': last['close'],
        'open': last['open']
    }

def detect_displacement(df_1m, sweep_info):
    """
    Check if the sweep candle (or the next candle) shows strong displacement.
    Displacement candle: large body in the direction opposite to the sweep.
    We'll consider the sweep candle itself if its body is strong and closes past the sweep level.
    Returns True if displacement sufficient, else False.
    """
    last = df_1m.iloc[-1]
    body_size = abs(last['close'] - last['open'])
    total_range = last['high'] - last['low']
    if total_range == 0:
        return False
    body_ratio = body_size / total_range  # 0 to 1
    # Determine if candle closed beyond the sweep level in the expected direction
    if sweep_info['expected_displacement'] == 'down':
        # For bearish displacement, we want close below sweep level
        closed_beyond = last['close'] < sweep_info['level']
        # Also, the candle should be bearish (close < open) ideally, but not required
    else:  # 'up'
        closed_beyond = last['close'] > sweep_info['level']
    return body_ratio >= MIN_DISP_STRENGTH and closed_beyond

def detect_mss(df_1m, sweep_info):
    """
    Detect Market Structure Shift: CHOCH then BOS in the direction opposite to the prior trend.
    We'll look for a change of character (first swing against prior trend) followed by a break of structure.
    Simplified: after sweep+displacement, we look for a candle that closes beyond the prior swing in the new direction.
    """
    if len(df_1m) < 3:
        return False
    # We'll consider the last two candles: the displacement candle and the one before it
    c1 = df_1m.iloc[-2]  # prior candle
    c2 = df_1m.iloc[-1]  # displacement/current candle
    # Determine prior trend based on swing points before sweep
    # For simplicity, we assume the sweep was of a high if expecting down displacement, etc.
    # We'll just check if the displacement candle closes beyond the swing level opposite to sweep.
    if sweep_info['expected_displacement'] == 'down':
        # Expecting bearish move: displacement should close below swing low
        return c2['close'] < sweep_info['level']
    else:
        # Expecting bullish move: displacement should close above swing high
        return c2['close'] > sweep_info['level']

def find_ob(df_1m, sweep_info):
    """
    Find Order Block: the last opposite-colored candle before the sweep that displaced price.
    We'll look back a few candles for the last candle opposite to the displacement direction.
    """
    if len(df_1m) < 5:
        return None
    # Displacement direction
    if sweep_info['expected_displacement'] == 'down':
        # We are looking for a bullish candle (close > open) before the sweep
        for i in range(-3, -10, -1):  # check last few candles before the last
            if len(df_1m) + i < 0:
                break
            c = df_1m.iloc[i]
            if c['close'] > c['open']:  # bullish candle
                return {
                    'high': c['high'],
                    'low': c['low'],
                    'open': c['open'],
                    'close': c['close']
                }
    else:
        # Expecting bullish displacement: look for bearish candle (close < open)
        for i in range(-3, -10, -1):
            if len(df_1m) + i < 0:
                break
            c = df_1m.iloc[i]
            if c['close'] < c['open']:  # bearish candle
                return {
                    'high': c['high'],
                    'low': c['low'],
                    'open': c['open'],
                    'close': c['close']
                }
    return None

def find_fvg(df_1m, sweep_info):
    """
    Find Fair Value Gap: 3-candle imbalance where C1.high < C3.low (bullish) or C1.low > C3.high (bearish).
    We'll scan the last few candles for an FVG that is relatively recent.
    """
    if len(df_1m) < 5:
        return None
    for i in range(-5, -1):
        if len(df_1m) + i < 0:
            break
        c1 = df_1m.iloc[i]
        c2 = df_1m.iloc[i+1]
        c3 = df_1m.iloc[i+2]
        # Bullish FVG: gap between c1.high and c3.low
        if c1['high'] < c3['low']:
            return {
                'type': 'bullish',
                'top': c3['low'],
                'bottom': c1['high'],
                'mid': (c1['high'] + c3['low']) / 2
            }
        # Bearish FVG: gap between c1.low and c3.high
        if c1['low'] > c3['high']:
            return {
                'type': 'bearish',
                'top': c1['low'],
                'bottom': c3['high'],
                'mid': (c1['low'] + c3['high']) / 2
            }
    return None

def get_confluence_zone(df_1m, sweep_info):
    """
    Determine the confluence zone: prioritize OB, then FVG, then midpoint of sweep level? Actually we want the OB or FVG.
    Return dict with 'type' ('OB' or 'FVG'), 'high', 'low', 'mid'.
    """
    ob = find_ob(df_1m, sweep_info)
    if ob is not None:
        return {
            'type': 'OB',
            'high': ob['high'],
            'low': ob['low'],
            'mid': (ob['high'] + ob['low']) / 2
        }
    fvg = find_fvg(df_1m, sweep_info)
    if fvg is not None:
        return {
            'type': 'FVG',
            'high': fvg['top'],
            'low': fvg['bottom'],
            'mid': fvg['mid']
        }
    return None

def get_ltf_trigger(df_1m, confluence_zone, bias):
    """
    Wait for price to enter the confluence zone, then look for a CHoCH or BOS on 1m in the direction of bias.
    Returns index of trigger candle if found, else None.
    """
    if confluence_zone is None:
        return None
    zone_high = confluence_zone['high']
    zone_low = confluence_zone['low']
    # We need to see price enter the zone, then break structure in our direction.
    # Simplified: look for a candle that closes within the zone and then a subsequent candle that breaks beyond the zone in the bias direction.
    # We'll implement a simple state machine: look for entry into zone, then breakout.
    entered = False
    for idx in range(len(df_1m)-1, -1, -1):  # iterate from most recent to older
        c = df_1m.iloc[idx]
        # Check if candle's body or wick enters the zone
        if (c['high'] >= zone_low and c['low'] <= zone_high):
            entered = True
        if entered:
            # After entry, look for a breakout in the bias direction
            if bias == 'up':
                # Need a close above zone_high (BOS) or a CHoCH? We'll use close > zone_high as trigger
                if c['close'] > zone_high:
                    return idx
            else:  # bias == 'down'
                if c['close'] < zone_low:
                    return idx
    return None

def calculate_sl_tp(df_1m, direction, sweep_info, confluence_zone):
    """
    Calculate stop loss and take profit levels.
    SL: beyond the sweep level (or OB origin if using OB).
    TP: next liquidity pool (we'll approximate as next swing high/low) or use StdDev/Fib.
    """
    # Stop loss: beyond the sweep level
    if direction == 'long':
        sl_price = sweep_info['level'] - (df_1m['high'].rolling(10).mean().iloc[-1] * 0.0001)  # a tiny buffer
        # Actually, we want SL just below the sweep level (for long, sweep was of low)
        # sweep_info['level'] is the swing low that was swept
        sl_price = sweep_info['level'] * 0.9999  # 0.01% below
    else:  # short
        sl_price = sweep_info['level'] * 1.0001  # 0.01% above
    # Take profit: next liquidity pool - we'll approximate as the next swing high/low in the direction of trade
    # For simplicity, we'll use a fixed risk-reward of 1:2 for now, but we can improve.
    # We'll compute SL distance and set TP at entry + 2*SL for long, entry - 2*SL for short.
    # This is a placeholder; replace with actual liquidity pool detection later.
    entry_price = df_1m.iloc[-1]['close']  # we will enter at close of trigger candle
    sl_distance = abs(entry_price - sl_price)
    if direction == 'long':
        tp_price = entry_price + 2 * sl_distance
    else:
        tp_price = entry_price - 2 * sl_distance
    return sl_price, tp_price

def calculate_position_size(equity, entry_price, sl_price):
    """
    Calculate lot size (quantity) based on risk % and stop loss distance.
    For futures, quantity is in contracts.
    """
    risk_amount = equity * RISK_PER_TRADE
    sl_distance = abs(entry_price - sl_price)
    if sl_distance == 0:
        return 0
    qty = risk_amount / sl_distance
    # For futures, we need to round to appropriate step size (e.g., 0.25 for ES)
    # We'll leave as float; the executor can round to lot size.
    return qty

def generate_signal(data_handler):
    """
    Main strategy function: returns a signal dict if conditions met, else None.
    """
    if not data_handler.is_market_open():
        return None
    if is_news_blackout():
        return None
    # Loop through each symbol
    for symbol in SYMBOLS:
        # Get latest candles for each timeframe we need
        df_1m = data_handler.get_latest(symbol, '1m', n=500)
        df_5m = data_handler.get_latest(symbol, '5m', n=500)
        df_15m = data_handler.get_latest(symbol, '15m', n=500)
        df_30m = data_handler.get_latest(symbol, '30m', n=500)
        df_1h = data_handler.get_latest(symbol, '1h', n=500)
        df_4h = data_handler.get_latest(symbol, '4h', n=500)
        df_1d = data_handler.get_latest(symbol, '1d', n=500)
        if df_1m.empty or df_1d.empty:
            continue
        # Determine HTF bias from daily
        bias = get_htf_bias(df_1d)
        if bias is None:
            continue
        # Detect sweep on 1m (using recent candles)
        sweep_info = detect_sweep(df_1m)
        if sweep_info is None:
            continue
        # Check displacement
        if not detect_displacement(df_1m, sweep_info):
            continue
        # Check MSS
        if not detect_mss(df_1m, sweep_info):
            continue
        # Find confluence (OB or FVG)
        confluence_zone = get_confluence_zone(df_1m, sweep_info)
        if confluence_zone is None:
            continue
        # Wait for LTF trigger
        trigger_idx = get_ltf_trigger(df_1m, confluence_zone, bias)
        if trigger_idx is None:
            continue
        # We have a signal!
        direction = 'long' if bias == 'up' else 'short'
        entry_price = df_1m.iloc[trigger_idx]['close']
        sl_price, tp_price = calculate_sl_tp(df_1m, direction, sweep_info, confluence_zone)
        equity = 100000.0  # placeholder; in main we will get from account
        qty = calculate_position_size(equity, entry_price, sl_price)
        return {
            'symbol': symbol,
            'direction': direction,
            'entry_price': entry_price,
            'sl_price': sl_price,
            'tp_price': tp_price,
            'quantity': qty,
            'reason': f"ICT+SMC: {bias} bias, sweep {sweep_info['type']}, displacement, MSS, {confluence_zone['type']} confluence",
            'timestamp': df_1m.index[trigger_idx]
        }
    return None