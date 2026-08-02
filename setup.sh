#!/bin/bash
# Volume Momentum Bot - Setup Script
# Run this to set up and start the bot

echo "============================================"
echo "  Volume Momentum Bot v1.0 - Setup"
echo "============================================"
echo ""

# Install dependencies
echo "[1/4] Installing dependencies..."
pip install -r requirements.txt

# Copy env file
echo "[2/4] Setting up configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please edit it with your Binance API keys."
else
    echo ".env file already exists."
fi

# Run backtest
echo "[3/4] Running backtest..."
python run_backtest.py

# Start bot
echo ""
echo "[4/4] Starting bot..."
echo "Press Ctrl+C to stop."
echo ""
python bot.py