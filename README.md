# Volume Momentum Bot

> **Aviso de riesgo:** software experimental con fines educativos. Corre en modo
> dry-run por defecto. Operar en vivo puede perder todo el capital. No es
> asesoría financiera.

Automated trading bot using Volume Momentum strategy (RSI of Volume + EMA crossover + Price Momentum).

## Features
- RSI of Volume indicator
- EMA trend confirmation
- Price momentum filter
- Risk management (1% per trade, 2% SL, 4% TP, capped to spot balance)
- Daily loss limit (the bot stops for the day when it is touched)
- Cooldown between signals (no re-entry right after an exit)
- Max simultaneous open positions
- Binance API integration (LOT_SIZE **and** MIN_NOTIONAL validation)
- Backtesting module (commissions included, honest position size)
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
- Position size capped to the available spot balance
- **Daily loss limit** (`MAX_DAILY_LOSS_PCT`, default 5%): when the day's loss
  reaches it, the bot stops opening positions for the rest of the day. The cut
  is sticky: a later win does not reopen the day.
- **Cooldown between signals** (`COOLDOWN_SECONDS`, default 300): after an exit,
  no new entry until the cooldown is over.
- **Max simultaneous positions** (`MAX_OPEN_POSITIONS`, default 1): if the cap
  is reached, the order is not sent.
- **Commissions** (`COMMISSION_PCT`, default 0.1%) are charged on both legs, in
  the backtester and in the live P&L.

All of these come from the `.env` (see `.env.example`): the values listed there
are the ones the bot actually reads.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Limitaciones conocidas

- No validado en testnet con órdenes reales: antes de operar en vivo hay que
  probarlo en Binance Testnet con órdenes de verdad.
- El límite diario se reinicia por día natural del reloj local, no por sesión
  de trading.
- Sin persistencia del P&L diario: si el proceso se cae, el día vuelve a
  empezar en cero.

## License
CC BY-NC 4.0 — uso no comercial. Para uso comercial, ver `SELLING.md`.
