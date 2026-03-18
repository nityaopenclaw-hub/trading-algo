import os
from datetime import date
from config import DAILY_LOSS_CAP, MAX_TRADES_PER_DAY, KILL_SWITCH_FILE

class RiskManager:
    def __init__(self):
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.current_date = date.today()
        self.reset_if_new_day()

    def reset_if_new_day(self):
        today = date.today()
        if today != self.current_date:
            self.daily_pnl = 0.0
            self.trades_today = 0
            self.current_date = today

    def add_pnl(self, pnl):
        self.reset_if_new_day()
        self.daily_pnl += pnl
        self.trades_today += 1

    def can_trade(self):
        self.reset_if_new_day()
        if os.path.exists(KILL_SWITCH_FILE):
            return False
        if self.daily_pnl <= -DAILY_LOSS_CAP:
            return False
        if self.trades_today >= MAX_TRADES_PER_DAY:
            return False
        return True

    def get_daily_pnl(self):
        self.reset_if_new_day()
        return self.daily_pnl

    def get_trades_today(self):
        self.reset_if_new_day()
        return self.trades_today