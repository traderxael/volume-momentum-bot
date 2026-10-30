"""
Volume Momentum Bot - Risk Management Module
"""
import math

class RiskManager:
    def __init__(self, risk_per_trade=0.01, stop_loss_pct=0.02, take_profit_pct=0.04,
                 commission_pct=0.001, max_daily_loss_pct=0.05,
                 max_open_positions=1, cooldown_seconds=300):
        self.risk_per_trade = risk_per_trade
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        # Las comisiones se cobran en las dos piernas. Sin contarlas, el
        # backtester miente y en vivo se pierde dinero sin que se note.
        self.commission_pct = commission_pct
        # Los tres limites que faltaban antes de operar en vivo (issue #1):
        # cuanto se puede perder por dia, cuantas posiciones abiertas a la vez
        # y cuanto se espera entre una salida y la siguiente entrada.
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_open_positions = max_open_positions
        self.cooldown_seconds = cooldown_seconds
        # El P&L del dia y si el limite ya se toco (ver daily_loss_exceeded).
        self.daily_pnl = 0.0
        self.daily_baseline = 0.0
        self.daily_breached = False

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

    # ---------- limite de perdida diaria ----------
    def reset_daily(self, balance):
        """Arranca un dia nuevo: el limite se recalcula sobre el balance actual."""
        self.daily_baseline = max(0.0, float(balance or 0.0))
        self.daily_pnl = 0.0
        self.daily_breached = False

    def record_trade_result(self, pnl):
        """Suma el resultado de una operacion (ya con comisiones) al dia."""
        self.daily_pnl += float(pnl or 0.0)
        if self.daily_baseline > 0 and self.daily_pnl <= -self.daily_loss_limit():
            self.daily_breached = True
        return self.daily_pnl

    def daily_loss_limit(self):
        """Cuanto se puede perder hoy, en dinero."""
        return self.daily_baseline * self.max_daily_loss_pct

    def daily_loss_exceeded(self):
        """True si el limite diario ya se toco.

        El corte es PEGAJOSO: una vez que se tocó, el dia se termina aunque una
        operacion despues recupere el P&L. Si no, el limite seria una sugerencia
        y no un limite.
        """
        return self.daily_breached

    def can_open_trade(self):
        """False si ya se perdio demasiado hoy."""
        return not self.daily_loss_exceeded()

    # ---------- cooldown entre senales ----------
    def cooldown_active(self, last_exit_ts, now):
        """True si todavia no se cumplio el cooldown desde la ultima salida."""
        if last_exit_ts is None or self.cooldown_seconds <= 0:
            return False
        return (now - last_exit_ts) < self.cooldown_seconds

    # ---------- posiciones simultaneas ----------
    def can_open_position(self, open_count):
        """True si todavia hay lugar para otra posicion abierta."""
        return open_count < self.max_open_positions

    # ---------- comisiones ----------
    def calculate_commission(self, entry_price, exit_price, quantity):
        """Comision total de la ida y la vuelta."""
        return (entry_price + exit_price) * quantity * self.commission_pct

    def calculate_pnl(self, entry_price, exit_price, side, quantity):
        """PnL neto: el bruto menos las comisiones de entrada y de salida."""
        if self._is_long(side):
            gross = (exit_price - entry_price) * quantity
        else:
            gross = (entry_price - exit_price) * quantity
        return gross - self.calculate_commission(entry_price, exit_price, quantity)