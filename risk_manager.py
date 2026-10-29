"""
Volume Momentum Bot - Risk Management Module
"""
import math

class RiskManager:
    def __init__(self, risk_per_trade=0.01, stop_loss_pct=0.02, take_profit_pct=0.04):
        self.risk_per_trade = risk_per_trade
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    @staticmethod
    def _is_long(side):
        return str(side).lower() in ('buy', 'long')

    def calculate_position_size(self, balance, entry_price, current_price=None):
        """Calculate position size based on risk percentage, capped to spot balance."""
        if not math.isfinite(balance) or not math.isfinite(entry_price):
            return 0.0
        if balance <= 0 or entry_price <= 0:
            return 0.0
        stop_distance = entry_price * self.stop_loss_pct
        if stop_distance <= 0:
            return 0.0
        risk_amount = balance * self.risk_per_trade
        position_size = risk_amount / stop_distance
        # Spot sin apalancamiento: el notional no puede superar el balance.
        max_size = balance / entry_price
        return min(position_size, max_size)

    def calculate_entry(self, signal_price, side='buy'):
        """Calculate entry price with slippage consideration."""
        slippage = 0.001  # 0.1% slippage
        if self._is_long(side):
            return signal_price * (1 + slippage)
        return signal_price * (1 - slippage)

    def calculate_sl_tp(self, entry_price, side='buy'):
        """Calculate stop loss and take profit prices."""
        if self._is_long(side):
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
        if self._is_long(side):
            return current_price <= entry_price * (1 - self.stop_loss_pct)
        return current_price >= entry_price * (1 + self.stop_loss_pct)

    def check_take_profit(self, current_price, entry_price, side):
        """Check if take profit has been hit."""
        if self._is_long(side):
            return current_price >= entry_price * (1 + self.take_profit_pct)
        return current_price <= entry_price * (1 - self.take_profit_pct)