# Volume Momentum Bot

Automated trading bot using Volume Momentum strategy (RSI of Volume + EMA crossover + Price Momentum).

## Features
- RSI of Volume indicator
- EMA trend confirmation
- Price momentum filter
- Risk management (1% per trade, 2% SL, 4% TP)
- Binance API integration
- Backtesting module
- Dry-run mode for safe testing

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure your API keys
cp .env.example .env
# Edit .env with your Binance API keys

# Run backtest
python run_backtest.py

# Run bot (dry run by default)
python bot.py
```

## Strategy Logic
Buy when: RSI Vol < 30 AND Volume > 1.5x avg AND Momentum > 0 AND Trend = Up
Sell when: RSI Vol > 70 AND Volume > 1.5x avg AND Momentum < 0 AND Trend = Down

## Risk Management
- 1% risk per trade
- 2% stop loss
- 4% take profit (2:1 R:R)
- Cooldown between signals

## License
MIT
