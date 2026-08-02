"""
Volume Momentum Bot - Binance Connector Module
Connects to Binance API for live trading and data fetching.
"""
import os
import logging
import pandas as pd
from datetime import datetime, timedelta
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
    def __init__(self):
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')
        self.dry_run = os.getenv('DRY_RUN', 'True').lower() == 'true'
        self.client = None
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

    def place_order(self, symbol, side, quantity, price=None):
        """Place a market or limit order."""
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