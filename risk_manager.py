"""
Volume Momentum Bot - Risk Management Module
"""
import pandas as pd
import numpy as np

class RiskManager:
    def __init__(self, risk_per_trade=0.01, stop_loss_pct=0.02, take_profit_pct=0.04):
        self.risk_per_trade = risk_per_trade
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def calculate_position_size(self, balance, entry_price, current_price=None):
        """Calculate position size based on risk percentage."""
        risk_amount = balance * self.risk_per_trade
        stop_distance = entry_price * self.stop_loss_pct
        if stop_distance == 0:
            return 0
        position_size = risk_amount / stop_distance
        return position_size

    def calculate_entry(self, signal_price, side='buy'):
        """Calculate entry price with slippage consideration."""
        slippage = 0.001  # 0.1% slippage
        if side == 'buy':
            return signal_price * (1 + slippage)
        return signal_price * (1 - slippage)

    def calculate_sl_tp(self, entry_price, side='buy'):
        """Calculate stop loss and take profit prices."""
        if side == 'buy':
            sl = entry_price * (1 - self.stop_loss_pct)
            tp = entry_price * (1 + self.take_profit_pct)
        else:
            sl = entry_price * (1 + self.stop_loss_pct)
            tp = entry_price * (1 - self.take_profit_pct)
        return sl, tp

    def calculate_rr(self, entry, sl, tp):
        """Calculate risk/reward ratio."""
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk == 0:
            return 0
        return reward / risk

    def check_stop_loss(self, current_price, entry_price, side):
        """Check if stop loss has been hit."""
        if side == 'buy':
            return current_price <= entry_price * (1 - self.stop_loss_pct)
        return current_price >= entry_price * (1 + self.stop_loss_pct)

    def check_take_profit(self, current_price, entry_price, side):
        """Check if take profit has been hit."""
        if side == 'buy':
            return current_price >= entry_price * (1 + self.take_profit_pct)
        return current_price <= entry_price * (1 - self.take_profit_pct)