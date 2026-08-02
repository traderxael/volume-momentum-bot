"""
Volume Momentum Bot - Backtest Runner
Run backtesting on historical data from Binance or generated sample.
"""
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategy import VolumeMomentumStrategy
from risk_manager import RiskManager
from backtester import Backtester

def generate_realistic_data():
    """Generate realistic BTC-like price data with volume spikes."""
    np.random.seed(42)
    n = 500
    dates = pd.date_range(start='2024-01-01', periods=n, freq='1h')

    # Simulate BTC price around 42000 with trends and volatility
    price = 42000.0
    prices = []
    volumes = []

    for i in range(n):
        # Add trend changes
        if i % 100 == 0:
            trend = np.random.choice([-1, 1]) * 0.001
        else:
            trend = 0

        change = np.random.normal(0.0002 + trend, 0.008)
        price *= (1 + change)
        prices.append(price)

        # Volume spikes during price moves
        base_vol = np.random.randint(800, 3000)
        vol_spike = 1.0
        if abs(change) > 0.01:
            vol_spike = np.random.uniform(2.0, 5.0)
        volumes.append(int(base_vol * vol_spike))

    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.004))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.004))) for p in prices],
        'close': prices,
        'volume': volumes
    })
    return df

def run_backtest():
    """Run the backtest."""
    print("=" * 60)
    print("VOLUME MOMENTUM BOT - BACKTEST")
    print("=" * 60)

    # Load data
    df = generate_realistic_data()
    print(f"Loaded {len(df)} candles of simulated BTC data")
    print(f"Price range: ${df['close'].min():.0f} - ${df['close'].max():.0f}")

    # Test multiple parameter sets
    configs = [
        {'name': 'Default', 'rsi_period': 14, 'rsi_ob': 70, 'rsi_os': 30,
         'ema_fast': 9, 'ema_slow': 21, 'vol_period': 20, 'vol_mult': 1.5},
        {'name': 'Aggressive', 'rsi_period': 10, 'rsi_ob': 75, 'rsi_os': 25,
         'ema_fast': 5, 'ema_slow': 13, 'vol_period': 14, 'vol_mult': 1.3},
        {'name': 'Conservative', 'rsi_period': 21, 'rsi_ob': 65, 'rsi_os': 35,
         'ema_fast': 12, 'ema_slow': 26, 'vol_period': 30, 'vol_mult': 2.0},
    ]

    best_report = None
    best_name = ''

    for config in configs:
        name = config.pop('name')
        strategy = VolumeMomentumStrategy(**config)
        risk = RiskManager(risk_per_trade=0.01, stop_loss_pct=0.02, take_profit_pct=0.04)
        backtester = Backtester(strategy, risk, initial_balance=1000)
        report = backtester.run(df)

        print(f"\n--- {name} Config ---")
        for key, value in report.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")

        if report.get('total_trades', 0) > 0:
            if best_report is None or report.get('win_rate', 0) > best_report.get('win_rate', 0):
                best_report = report
                best_name = name

    if best_report:
        print(f"\n{'=' * 60}")
        print(f"BEST CONFIG: {best_name}")
        print(f"{'=' * 60}")
        for key, value in best_report.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")

    # Save best trades
    if best_report and best_report.get('total_trades', 0) > 0:
        strategy = VolumeMomentumStrategy(**configs[0])
        risk = RiskManager()
        bt = Backtester(strategy, risk, initial_balance=1000)
        bt.run(df)
        if bt.trades:
            trades_df = pd.DataFrame(bt.trades)
            trades_df.to_csv('backtest_trades.csv', index=False)
            print(f"\nTrades saved to backtest_trades.csv")

    return best_report

if __name__ == '__main__':
    run_backtest()