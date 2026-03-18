import csv
import os
from datetime import datetime

class TradeLogger:
    def __init__(self, log_file="trades.csv"):
        self.log_file = log_file
        # Ensure the log file exists with headers
        if not os.path.isfile(self.log_file):
            with open(self.log_file, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "symbol", "side", "entry_price", "sl_price", "tp_price",
                    "quantity", "pnl", "reason", "emotion"
                ])

    def log_trade(self, timestamp, symbol, side, entry, sl, tp, qty, pnl, reason, emotion=""):
        with open(self.log_file, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, symbol, side, entry, sl, tp, qty, pnl, reason, emotion
            ])

    def read_trades(self):
        if not os.path.isfile(self.log_file):
            return []
        with open(self.log_file, mode='r') as f:
            reader = csv.DictReader(f)
            return list(reader)