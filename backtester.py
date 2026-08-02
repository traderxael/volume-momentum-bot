"""
Volume Momentum Bot - Backtesting Module
"""
import pandas as pd
import numpy as np
from strategy import VolumeMomentumStrategy
from risk_manager import RiskManager

class Backtester:
    def __init__(self, strategy, risk_manager, initial_balance=1000):
        self.strategy = strategy
        self.risk = risk_manager
        self.initial_balance = initial_balance
        self.trades = []

    def run(self, df):
        """Run backtest on historical data."""
        df = self.strategy.generate_signals(df)
        balance = self.initial_balance
        position = None  # None, 'long', or 'short'
        entry_price = 0
        entry_idx = 0

        for i in range(len(df)):
            row = df.iloc[i]
            current_price = row['close']
            signal = row['signal']

            # Check exit conditions
            if position is not None:
                sl_hit = self.risk.check_stop_loss(current_price, entry_price, position)
                tp_hit = self.risk.check_take_profit(current_price, entry_price, position)

                if sl_hit or tp_hit:
                    exit_price = current_price
                    pnl = self._calculate_pnl(exit_price, entry_price, position)
                    balance += pnl
                    self.trades.append({
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'side': position,
                        'pnl': pnl,
                        'balance': balance,
                        'reason': 'SL' if sl_hit else 'TP'
                    })
                    position = None
                    continue

            # Check for new entry
            if position is None and signal != 0:
                position_size = self.risk.calculate_position_size(
                    balance, current_price
                )
                if position_size > 0 and balance > 10:  # Min balance check
                    position = 'long' if signal == 1 else 'short'
                    entry_price = self.risk.calculate_entry(current_price, position)
                    entry_idx = i

        return self._generate_report()

    def _calculate_pnl(self, exit_price, entry_price, side):
        """Calculate profit/loss for a trade."""
        if side == 'long':
            return (exit_price - entry_price) * self.risk.calculate_position_size(
                self.initial_balance, entry_price
            )
        else:
            return (entry_price - exit_price) * self.risk.calculate_position_size(
                self.initial_balance, entry_price
            )

    def _generate_report(self):
        """Generate backtest report."""
        if len(self.trades) == 0:
            return {'total_trades': 0, 'message': 'No trades executed'}

        trades_df = pd.DataFrame(self.trades)
        wins = trades_df[trades_df['pnl'] > 0]
        losses = trades_df[trades_df['pnl'] < 0]

        report = {
            'total_trades': len(self.trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(self.trades) * 100,
            'total_pnl': trades_df['pnl'].sum(),
            'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0,
            'max_drawdown': (self.initial_balance - trades_df['balance'].min()) / self.initial_balance * 100,
            'final_balance': trades_df['balance'].iloc[-1] if len(trades_df) > 0 else self.initial_balance,
            'profit_factor': abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else float('inf'),
            'avg_rr': trades_df.apply(
                lambda t: self.risk.calculate_rr(t['entry_price'], 
                    t['entry_price'] * (1 - self.risk.stop_loss_pct) if t['side'] == 'long'
                    else t['entry_price'] * (1 + self.risk.stop_loss_pct),
                    t['entry_price'] * (1 + self.risk.take_profit_pct) if t['side'] == 'long'
                    else t['entry_price'] * (1 - self.risk.take_profit_pct)), axis=1
            ).mean() if len(self.trades) > 0 else 0
        }
        return report