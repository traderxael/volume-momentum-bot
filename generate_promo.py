#!/usr/bin/env python3
"""
Volume Momentum Bot - Distribution Script
Generates promotional content and distribution links.
"""

import json
from datetime import datetime

PRODUCT_NAME = "Volume Momentum Bot"
PRODUCT_VERSION = "1.0.0"
AUTHOR = "Axael"
EMAIL = "mathialuke@gmail.com"
TELEGRAM = "@DREstebot"

# Promotional messages for different platforms
promotions = {
    "telegram": f"""
🎯 {PRODUCT_NAME} v{PRODUCT_VERSION}

Automated trading bot using Volume Momentum strategy.
RSI of Volume + EMA crossover + Price Momentum.

✅ Works with Binance (BTC/USDT and any pair)
✅ Dry-run mode for safe testing
✅ Risk management built-in (1% risk, 2% SL, 4% TP)
✅ Backtesting engine included
✅ Full documentation

💰 Pricing:
• Personal license: $29.99
• Commercial license: $79.99
• Setup + Bot: $49.99

📦 What's included:
• bot.py - Main trading bot
• strategy.py - Volume Momentum strategy
• risk_manager.py - Risk management
• binance_connector.py - Binance API integration
• backtester.py - Backtesting engine
• volume_momentum_v1.pine - TradingView indicator
• README + full documentation

⚡ Setup time: 5 minutes

Contact: {EMAIL} or {TELEGRAM}
""",

    "gumroad_description": f"""
Volume Momentum Bot v{PRODUCT_VERSION}

An automated trading bot that uses the Volume Momentum strategy to generate buy/sell signals on Binance.

Strategy combines:
• RSI of Volume (measures volume strength)
• EMA crossover (confirms trend direction)
• Price momentum filter (avoids counter-trend signals)
• Volume ratio filter (only trades when volume confirms)

Includes:
• Full Python bot with Binance API integration
• TradingView indicator (Pine Script)
• Backtesting engine
• Risk management (configurable)
• Dry-run mode
• Trading journal template

Requirements:
• Python 3.8+
• Binance account with API keys
• $100+ starting capital recommended

Support: {EMAIL}
""",

    "twitter_post": f"""
🤖 New: Volume Momentum Bot — automated crypto trading bot

Strategy: RSI of Volume + EMA crossover + Price Momentum
Platform: Binance
Risk: 1% per trade, 2% SL, 4% TP (2:1 R:R)
Dry-run mode included

$29.99 personal | $79.99 commercial
DM for details 📩
""",

    "email_template": f"""
Subject: Volume Momentum Bot — Automated Trading Bot ($29.99)

Hi,

I've built an automated trading bot called Volume Momentum Bot.

It uses a strategy combining:
• RSI of Volume (measures volume strength, not just price)
• EMA trend confirmation (9/21)
• Price momentum filter (10-period)
• Volume ratio filter (only trades when volume > 1.5x average)

The bot includes:
• Full Python source code
• Binance API integration (dry-run + live)
• Backtesting engine
• Risk management (1% risk, 2% SL, 4% TP)
• TradingView indicator (companion)
• Trading journal template
• Full documentation

Setup takes ~5 minutes.

Pricing:
• Personal license: $29.99
• Commercial license: $79.99
• Setup + Bot: $49.99

Get it here: [LINK]

Questions? Reach out: {EMAIL}

Best,
{AUTHOR}
"""
}

# Save all promotions to files
import os
output_dir = os.path.dirname(os.path.abspath(__file__))

for platform, content in promotions.items():
    filepath = os.path.join(output_dir, f'promo_{platform}.txt')
    with open(filepath, 'w') as f:
        f.write(content.strip())
    print(f"Saved: {filepath}")

print(f"\nAll promotional content generated at {datetime.now().isoformat()}")
print(f"Files created in: {output_dir}")
