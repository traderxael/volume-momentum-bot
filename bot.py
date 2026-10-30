"""
Volume Momentum Bot - Main Bot Module
Orchestrates strategy, risk management, and Binance connection.
"""
import os
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
    # La configuracion sale del .env (ver .env.example). Antes estos valores
    # eran decorativos: el bot los declaraba pero nunca los leia, asi que los
    # limites no se podian cambiar sin tocar el codigo.
    _CONFIG_KEYS = {
        'SYMBOL': str,
        'TIMEFRAME': str,
        'RSI_PERIOD': int,
        'RSI_OVERBOUGHT': int,
        'RSI_OVERSOLD': int,
        'EMA_FAST': int,
        'EMA_SLOW': int,
        'VOL_PERIOD': int,
        'VOL_MULTIPLIER': float,
        'RISK_PER_TRADE': float,
        'STOP_LOSS_PCT': float,
        'TAKE_PROFIT_PCT': float,
        'COMMISSION_PCT': float,
        'MAX_DAILY_LOSS_PCT': float,
        'MAX_OPEN_POSITIONS': int,
        'COOLDOWN_SECONDS': int,
        'DRY_RUN': bool,
    }

    @classmethod
    def _config_from_env(cls):
        """Lee la configuracion del entorno, con su tipo y sin romper nada."""
        config = {}
        for key, cast in cls._CONFIG_KEYS.items():
            raw = os.getenv(key)
            if raw is None or raw.strip() == '':
                continue
            try:
                if cast is bool:
                    config[key] = raw.strip().lower() in ('1', 'true', 'yes', 'on')
                else:
                    config[key] = cast(raw)
            except (TypeError, ValueError):
                logger.warning(
                    f"Valor invalido para {key}: {raw!r}. Se usa el valor por defecto."
                )
        return config

    def __init__(self, config=None):
        self.config = config if config is not None else self._config_from_env()
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
            take_profit_pct=self.config.get('TAKE_PROFIT_PCT', 0.04),
            commission_pct=self.config.get('COMMISSION_PCT', 0.001),
            max_daily_loss_pct=self.config.get('MAX_DAILY_LOSS_PCT', 0.05),
            max_open_positions=self.config.get('MAX_OPEN_POSITIONS', 1),
            cooldown_seconds=self.config.get('COOLDOWN_SECONDS', 300)
        )
        self.dry_run = self.config.get('DRY_RUN', True)
        self.binance = BinanceConnector(dry_run=self.dry_run)
        self.symbol = self.config.get('SYMBOL', 'BTCUSDT')
        self.timeframe = self.config.get('TIMEFRAME', '1h')
        # Las posiciones abiertas. El bot es spot de un simbolo, asi que hoy
        # hay una sola, pero el limite es explicito: si se abre mas de la
        # cuenta, no se manda la orden.
        self.open_positions = []
        self.max_open_positions = self.config.get('MAX_OPEN_POSITIONS', 1)
        self.cooldown_seconds = self.config.get('COOLDOWN_SECONDS', 300)
        # Cuando se cerro la ultima posicion: a partir de ahi hay cooldown.
        self.last_exit_time = None
        # Reloj inyectable: los tests no duermen, avanzan el reloj.
        self._clock = self.config.get('CLOCK', time.time)
        self._current_day = None
        self.trade_log = []

    @property
    def active_position(self):
        """La posicion abierta actual (la ultima)."""
        return self.open_positions[-1] if self.open_positions else None

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

        # --- los limites van ANTES de la orden ---
        # Con el limite diario saltado, en cooldown, o con el cupo de
        # posiciones lleno, no se manda nada a Binance.
        now = self._clock()
        if not self.risk.can_open_trade():
            logger.warning(
                "Limite diario de perdida alcanzado: hoy no se abre ninguna operacion."
            )
            return None
        if self.risk.cooldown_active(self.last_exit_time, now):
            faltan = int(self.cooldown_seconds - (now - self.last_exit_time))
            logger.info(f"Cooldown activo: faltan {faltan}s para la proxima entrada.")
            return None
        if not self.risk.can_open_position(len(self.open_positions)):
            logger.warning(
                f"No se abre la posicion: ya hay {len(self.open_positions)} abiertas "
                f"(maximo {self.max_open_positions})."
            )
            return None

        balance = self.binance.get_balance().get('USDT', 0.0)
        if balance <= 0:
            logger.error("No hay balance USDT disponible. Se omite la operación.")
            return None
        if self.risk.daily_baseline <= 0:
            # Primera operacion del dia: el limite se mide sobre este balance.
            self.risk.reset_daily(balance)
        position_size = self.risk.calculate_position_size(balance, price)

        if position_size <= 0:
            logger.warning("Position size is 0. Skipping trade.")
            return None

        logger.info(f"Signal: {side} | Price: {price} | Size: {position_size:.6f}")

        # Place order
        order = self.binance.place_order(
            symbol=self.symbol,
            side=side,
            quantity=position_size,
            price=None  # Market order
        )
        if order.get('status') == 'ERROR':
            logger.error(f"Binance rechazo la orden: {order.get('message')}")
            return None

        # Set SL and TP
        sl, tp = self.risk.calculate_sl_tp(price, 'long' if signal == 1 else 'short')

        position = {
            'side': 'long' if signal == 1 else 'short',
            'entry_price': price,
            'quantity': position_size,
            'stop_loss': sl,
            'take_profit': tp,
            'entry_time': datetime.now(),
            'order_id': order.get('orderId')
        }
        self.open_positions.append(position)

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

        return position

    def _close_position(self, current_price):
        """Close current position."""
        if not self.open_positions:
            return

        pos = self.open_positions[-1]
        close_side = 'SELL' if pos['side'] == 'long' else 'BUY'

        order = self.binance.place_order(
            symbol=self.symbol,
            side=close_side,
            quantity=pos['quantity'],
            price=None
        )

        pnl = (current_price - pos['entry_price']) * pos['quantity'] if pos['side'] == 'long' \
              else (pos['entry_price'] - current_price) * pos['quantity']
        # Lo que cuenta para el limite diario es el P&L NETO (con comisiones).
        net_pnl = self.risk.calculate_pnl(
            pos['entry_price'], current_price, pos['side'], pos['quantity']
        )
        self.risk.record_trade_result(net_pnl)
        # El cooldown arranca con la salida, no con la entrada.
        self.last_exit_time = self._clock()

        self.trade_log.append({
            'time': datetime.now().isoformat(),
            'action': 'EXIT',
            'side': close_side,
            'price': current_price,
            'pnl': pnl,
            'net_pnl': net_pnl,
            'order': order
        })

        logger.info(f"Position closed. P&L: ${pnl:.2f} (neto ${net_pnl:.2f})")
        self.open_positions.pop()

    def _refresh_daily_limit(self, balance):
        """Si cambio el dia, el limite diario de perdida se reinicia."""
        today = datetime.fromtimestamp(self._clock()).date()
        if self._current_day != today:
            self._current_day = today
            self.risk.reset_daily(balance)
            logger.info("Nuevo dia: el limite diario de perdida se reinicia.")

    def run_once(self):
        """Run one analysis cycle."""
        # El limite diario se reinicia solo cuando cambia el dia.
        self._refresh_daily_limit(self.binance.get_balance().get('USDT', 0.0))
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