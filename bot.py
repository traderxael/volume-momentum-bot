"""
Volume Momentum Bot - Main Bot Module
Orchestrates strategy, risk management, and Binance connection.
"""
import time
import logging
import pandas as pd
from datetime import datetime
from strategy import VolumeMomentumStrategy
from risk_manager import RiskManager
from binance_connector import BinanceConnector
from backtester import Backtester

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VolumeMomentumBot')

class TradingBot:
    def __init__(self, config=None):
        self.config = config or {}
        self.strategy = VolumeMomentumStrategy(
            rsi_period=self.config.get('RSI_PERIOD', 14),
            rsi_ob=self.config.get('RSI_OVERBOUGHT', 70),
            rsi_os=self.config.get('RSI_OVERSOLD', 30),
            ema_fast=self.config.get('EMA_FAST', 9),
            ema_slow=self.config.get('EMA_SLOW', 21),
            vol_period=self.config.get('VOL_PERIOD', 20),
            vol_mult=self.config.get('VOL_MULTIPLIER', 1.5)
        )
        self.risk = RiskManager(
            risk_per_trade=self.config.get('RISK_PER_TRADE', 0.01),
            stop_loss_pct=self.config.get('STOP_LOSS_PCT', 0.02),
            take_profit_pct=self.config.get('TAKE_PROFIT_PCT', 0.04)
        )
        self.binance = BinanceConnector()
        self.symbol = self.config.get('SYMBOL', 'BTCUSDT')
        self.timeframe = self.config.get('TIMEFRAME', '1h')
        self.dry_run = self.config.get('DRY_RUN', True)
        self.active_position = None
        self.trade_log = []

    def fetch_data(self):
        """Fetch latest market data."""
        df = self.binance.get_klines(
            symbol=self.symbol,
            interval=self.timeframe,
            limit=200
        )
        return df

    def analyze(self):
        """Run analysis and return current signal."""
        df = self.fetch_data()
        if df.empty:
            logger.warning("No data available for analysis")
            return None, None, None

        df = self.strategy.generate_signals(df)
        last_row = df.iloc[-1]
        signal = last_row['signal']
        price = last_row['close']
        rsi_vol = last_row['rsi_vol']

        return signal, price, rsi_vol

    def execute_trade(self, signal, price):
        """Execute a trade based on signal."""
        if signal == 0:
            return None

        side = 'BUY' if signal == 1 else 'SELL'
        position_size = self.risk.calculate_position_size(1000, price)  # Will use real balance in production

        if position_size <= 0:
            logger.warning("Position size is 0. Skipping trade.")
            return None

        logger.info(f"Signal: {side} | Price: {price} | Size: {position_size:.6f}")

        # Check if we already have a position
        if self.active_position is not None:
            logger.info(f"Already in {self.active_position} position. Closing first.")
            self._close_position(price)

        # Place order
        order = self.binance.place_order(
            symbol=self.symbol,
            side=side,
            quantity=position_size,
            price=None  # Market order
        )

        # Set SL and TP
        sl, tp = self.risk.calculate_sl_tp(price, 'long' if signal == 1 else 'short')

        self.active_position = {
            'side': 'long' if signal == 1 else 'short',
            'entry_price': price,
            'quantity': position_size,
            'stop_loss': sl,
            'take_profit': tp,
            'entry_time': datetime.now(),
            'order_id': order.get('orderId')
        }

        self.trade_log.append({
            'time': datetime.now().isoformat(),
            'action': 'ENTRY',
            'side': side,
            'price': price,
            'quantity': position_size,
            'sl': sl,
            'tp': tp,
            'order': order
        })

        return self.active_position

    def _close_position(self, current_price):
        """Close current position."""
        if self.active_position is None:
            return

        pos = self.active_position
        close_side = 'SELL' if pos['side'] == 'long' else 'BUY'

        order = self.binance.place_order(
            symbol=self.symbol,
            side=close_side,
            quantity=pos['quantity'],
            price=None
        )

        pnl = (current_price - pos['entry_price']) * pos['quantity'] if pos['side'] == 'long' \
              else (pos['entry_price'] - current_price) * pos['quantity']

        self.trade_log.append({
            'time': datetime.now().isoformat(),
            'action': 'EXIT',
            'side': close_side,
            'price': current_price,
            'pnl': pnl,
            'order': order
        })

        logger.info(f"Position closed. P&L: ${pnl:.2f}")
        self.active_position = None

    def run_once(self):
        """Run one analysis cycle."""
        signal, price, rsi_vol = self.analyze()
        if signal is None:
            return

        logger.info(f"Analysis: Signal={signal}, Price={price}, RSI Vol={rsi_vol:.1f}")

        if signal != 0 and self.active_position is None:
            self.execute_trade(signal, price)
        elif signal == 0 and self.active_position is not None:
            # Check if we should close (opposite signal or SL/TP hit)
            pos = self.active_position
            if self.risk.check_stop_loss(price, pos['entry_price'], pos['side']):
                logger.info("Stop loss hit!")
                self._close_position(price)
            elif self.risk.check_take_profit(price, pos['entry_price'], pos['side']):
                logger.info("Take profit hit!")
                self._close_position(price)

    def run_continuous(self, interval_seconds=3600):
        """Run bot continuously at specified intervals."""
        logger.info(f"Starting bot in {'DRY RUN' if self.dry_run else 'LIVE'} mode")
        logger.info(f"Symbol: {self.symbol} | Timeframe: {self.timeframe}")

        while True:
            try:
                self.run_once()
                logger.info(f"Waiting {interval_seconds}s until next cycle...")
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)

    def get_trade_log(self):
        """Return the trade log."""
        return pd.DataFrame(self.trade_log)

    def get_performance(self):
        """Calculate basic performance metrics."""
        if not self.trade_log:
            return {'message': 'No trades executed yet'}

        df = pd.DataFrame(self.trade_log)
        exits = df[df['action'] == 'EXIT']
        if len(exits) == 0:
            return {'message': 'No closed trades yet'}

        total_pnl = exits['pnl'].sum() if 'pnl' in exits.columns else 0
        wins = exits[exits['pnl'] > 0] if 'pnl' in exits.columns else pd.DataFrame()
        losses = exits[exits['pnl'] < 0] if 'pnl' in exits.columns else pd.DataFrame()

        return {
            'total_trades': len(exits),
            'win_rate': len(wins) / len(exits) * 100 if len(exits) > 0 else 0,
            'total_pnl': total_pnl,
            'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0
        }


if __name__ == '__main__':
    bot = TradingBot()
    bot.run_once()