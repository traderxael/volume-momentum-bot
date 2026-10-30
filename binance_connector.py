"""
Volume Momentum Bot - Binance Connector Module
Connects to Binance API for live trading and data fetching.
"""
import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('VolumeMomentumBot')

class BinanceConnector:
    def __init__(self, dry_run=None):
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')
        self.dry_run = dry_run if dry_run is not None else os.getenv('DRY_RUN', 'True').lower() == 'true'
        self.client = None
        self._filters = {}
        self._connect()

    def _connect(self):
        """Initialize Binance client."""
        try:
            from binance.client import Client
            self.client = Client(self.api_key, self.api_secret)
            # Test connection
            self.client.get_account()
            logger.info("Connected to Binance API successfully")
        except ImportError:
            logger.warning("python-binance not installed. Using data-only mode.")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            self.client = None

    def get_klines(self, symbol='BTCUSDT', interval='1h', limit=200):
        """Fetch historical klines/candlestick data."""
        if self.client is None:
            logger.warning("No Binance connection. Returning empty data.")
            return pd.DataFrame()
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'trades',
                'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            df['open'] = pd.to_numeric(df['open'], errors='coerce')
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logger.error(f"Error fetching klines: {e}")
            return pd.DataFrame()

    def get_balance(self):
        """Get account balance."""
        if self.client is None or self.dry_run:
            return {'USDT': 1000.0}  # Simulated balance
        try:
            account = self.client.get_account()
            balances = {}
            for b in account['balances']:
                if float(b['free']) > 0 or float(b['locked']) > 0:
                    balances[b['asset']] = float(b['free']) + float(b['locked'])
            return balances
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return {}

    def _symbol_filters(self, symbol):
        """Filtros del simbolo en Binance, con cache por simbolo."""
        filters = self._filters.get(symbol)
        if filters is None:
            info = self.client.get_symbol_info(symbol)
            filters = {f['filterType']: f for f in (info or {}).get('filters', [])}
            self._filters[symbol] = filters
        return filters

    def _round_quantity(self, symbol, quantity):
        """Round quantity down to the symbol LOT_SIZE step."""
        if self.client is None:
            return quantity
        try:
            filters = self._symbol_filters(symbol)
            lot = filters.get('LOT_SIZE')
            if not lot:
                return quantity
            step = Decimal(lot['stepSize'])
            if step <= 0:
                return quantity
            value = (Decimal(str(quantity)) / step).to_integral_value(rounding=ROUND_DOWN) * step
            if value < Decimal(lot['minQty']):
                return 0.0
            return float(value)
        except Exception as e:
            logger.warning(f"No se pudo redondear la cantidad: {e}")
            return quantity

    def _min_notional(self, symbol):
        """El MIN_NOTIONAL del simbolo (5 USDT en BTCUSDT). None si no se sabe."""
        if self.client is None:
            return None
        try:
            filters = self._symbol_filters(symbol)
        except Exception as e:
            logger.warning(f"No se pudieron leer los filtros de {symbol}: {e}")
            return None
        min_notional = filters.get('MIN_NOTIONAL')
        if not min_notional:
            return None
        try:
            value = float(min_notional.get('minNotional', 0))
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    def _reference_price(self, symbol, price):
        """El precio contra el que se mide el notional (el ultimo si es a mercado)."""
        if price is not None:
            try:
                return float(price)
            except (TypeError, ValueError):
                return None
        if self.client is None:
            return None
        try:
            ticker = self.client.get_symbol_ticker(symbol)
            return float(ticker['price'])
        except Exception as e:
            logger.warning(f"No se pudo obtener el precio de {symbol}: {e}")
            return None

    def _validate_notional(self, symbol, quantity, price):
        """True si la orden cumple el MIN_NOTIONAL del simbolo.

        El LOT_SIZE mira la CANTIDAD; el MIN_NOTIONAL mira el VALOR. Una orden
        de 0.01 BTC cumple el LOT_SIZE pero vale 1 USDT, y Binance la rebota.
        """
        min_notional = self._min_notional(symbol)
        if not min_notional:
            return True
        ref_price = self._reference_price(symbol, price)
        if ref_price is None or ref_price <= 0:
            # Sin precio no hay forma de medir el notional: no se bloquea la
            # orden, pero queda dicho en el log.
            logger.warning(f"No se pudo medir el notional de {symbol}: se envia la orden.")
            return True
        notional = quantity * ref_price
        if notional < min_notional:
            logger.error(
                f"Orden rechazada: notional {notional:.4f} USDT < MIN_NOTIONAL "
                f"{min_notional} USDT en {symbol}."
            )
            return False
        return True

    def place_order(self, symbol, side, quantity, price=None):
        """Place a market or limit order."""
        quantity = self._round_quantity(symbol, quantity)
        if quantity <= 0:
            logger.error(f"Cantidad inválida para {symbol}: por debajo del LOT_SIZE mínimo.")
            return {'status': 'ERROR', 'message': 'quantity below LOT_SIZE'}
        if not self._validate_notional(symbol, quantity, price):
            return {
                'status': 'ERROR',
                'message': f'notional below MIN_NOTIONAL for {symbol}'
            }
        if self.dry_run:
            logger.info(f"[DRY RUN] Would place {side} order: {quantity} {symbol} at {price or 'market'}")
            return {'status': 'DRY_RUN', 'side': side, 'quantity': quantity}
        if self.client is None:
            logger.error("No Binance connection. Cannot place order.")
            return {'status': 'ERROR', 'message': 'No connection'}
        try:
            if price:
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type='LIMIT',
                    quantity=quantity,
                    price=price,
                    timeInForce='GTC'
                )
            else:
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type='MARKET',
                    quantity=quantity
                )
            logger.info(f"Order placed: {order['orderId']} - {side} {quantity} {symbol}")
            return order
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {'status': 'ERROR', 'message': str(e)}