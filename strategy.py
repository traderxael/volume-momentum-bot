"""
Volume Momentum Bot - Trading Strategy Module
Strategy: RSI of Volume + EMA crossover + Price Momentum
"""
import pandas as pd
import numpy as np
import ta

class VolumeMomentumStrategy:
    def __init__(self, rsi_period=14, rsi_ob=70, rsi_os=30,
                 ema_fast=9, ema_slow=21, vol_period=20, vol_mult=1.5):
        self.rsi_period = rsi_period
        self.rsi_ob = rsi_ob
        self.rsi_os = rsi_os
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.vol_period = vol_period
        self.vol_mult = vol_mult

    def calculate_indicators(self, df):
        """Calculate all strategy indicators."""
        df = df.copy()

        # RSI of Volume
        vol_change = df['volume'].diff()
        vol_gain = vol_change.clip(lower=0)
        vol_loss = (-vol_change).clip(lower=0)
        avg_gain = vol_gain.ewm(span=self.vol_period, min_periods=1).mean()
        avg_loss = vol_loss.ewm(span=self.vol_period, min_periods=1).mean()
        rs_vol = avg_gain / avg_loss.replace(0, np.nan)
        df['rsi_vol'] = 100 - (100 / (1 + rs_vol))
        df['rsi_vol'] = df['rsi_vol'].fillna(50)

        # EMAs
        df['ema_fast'] = ta.trend.ema_indicator(df['close'], window=self.ema_fast)
        df['ema_slow'] = ta.trend.ema_indicator(df['close'], window=self.ema_slow)

        # Price momentum
        df['momentum'] = df['close'].pct_change(periods=10) * 100

        # Volume ratio
        df['vol_avg'] = df['volume'].rolling(window=self.vol_period).mean()
        df['vol_ratio'] = df['volume'] / df['vol_avg']

        # Trend
        df['trend_up'] = df['ema_fast'] > df['ema_slow']

        return df

    def generate_signals(self, df):
        """Generate buy/sell signals."""
        df = self.calculate_indicators(df)

        df['signal'] = 0  # 0 = hold
        df.loc[
            (df['rsi_vol'] < self.rsi_os) &
            (df['vol_ratio'] > self.vol_mult) &
            (df['momentum'] > 0) &
            (df['trend_up']),
            'signal'
        ] = 1  # BUY

        df.loc[
            (df['rsi_vol'] > self.rsi_ob) &
            (df['vol_ratio'] > self.vol_mult) &
            (df['momentum'] < 0) &
            (~df['trend_up']),
            'signal'
        ] = -1  # SELL

        return df

    def get_last_signal(self, df):
        """Get the most recent signal."""
        df = self.calculate_indicators(df)
        signals = df[df['signal'] != 0].tail(1)
        if len(signals) == 0:
            return None, None, None
        row = signals.iloc[0]
        return row['signal'], row['close'], row['rsi_vol']