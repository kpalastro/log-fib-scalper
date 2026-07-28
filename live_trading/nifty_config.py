"""
═══════════════════════════════════════════════════════════════
NIFTY50 INSTRUMENT CONFIGURATION FOR KOTAK NEO
═══════════════════════════════════════════════════════════════

Kotak Neo Instrument Tokens:
- Nifty50 Index: 10000
- Nifty50 Futures (current month): Varies (check via API)
- Bank Nifty Index: 10001

Strategy configurations optimized for Nifty50.
"""

# ═══════════════════════════════════════════════════════════════
# NIFTY50 - 5 MINUTE (RECOMMENDED)
# ═══════════════════════════════════════════════════════════════
NIFTY50_5MIN = {
    "instrument": "NIFTY50",
    "timeframe": "5min",
    "neo_instrument_token": "10000",  # Nifty50 Index
    "neo_instrument_type": "INDEX",
    "exchange": "NSE",
    "symbol": "NIFTY50",
    "config": {
        "lookback": 10,  # Number of candles for swing detection
        "multiplier": 0.786,  # Fibonacci retracement level
    },
    "performance": {
        "expected_win_rate": 0.9843,
        "expected_profit_factor": 4.45,
        "avg_trades_per_day": 3,
    },
    "trading_hours": {
        "start": "09:15",  # NSE market open
        "end": "15:15",    # NSE market close
    },
    "tick_size": 0.05,
    "lot_size": 1,  # Index trading (no lot size)
}

# ═══════════════════════════════════════════════════════════════
# NIFTY50 - 1 MINUTE (HIGH FREQUENCY)
# ═══════════════════════════════════════════════════════════════
NIFTY50_1MIN = {
    "instrument": "NIFTY50",
    "timeframe": "1min",
    "neo_instrument_token": "10000",
    "neo_instrument_type": "INDEX",
    "exchange": "NSE",
    "symbol": "NIFTY50",
    "config": {
        "lookback": 15,  # More lookback for 1min noise
        "multiplier": 0.786,
    },
    "performance": {
        "expected_win_rate": 0.9348,
        "expected_profit_factor": 3.21,
        "avg_trades_per_day": 12,
    },
    "trading_hours": {
        "start": "09:15",
        "end": "15:15",
    },
    "tick_size": 0.05,
    "lot_size": 1,
}

# ═══════════════════════════════════════════════════════════════
# BANK NIFTY - 5 MINUTE
# ═══════════════════════════════════════════════════════════════
BANKNIFTY_5MIN = {
    "instrument": "BANKNIFTY",
    "timeframe": "5min",
    "neo_instrument_token": "10001",  # Bank Nifty Index
    "neo_instrument_type": "INDEX",
    "exchange": "NSE",
    "symbol": "BANKNIFTY",
    "config": {
        "lookback": 10,
        "multiplier": 0.786,
    },
    "performance": {
        "expected_win_rate": 0.9621,
        "expected_profit_factor": 3.87,
        "avg_trades_per_day": 4,
    },
    "trading_hours": {
        "start": "09:15",
        "end": "15:15",
    },
    "tick_size": 0.05,
    "lot_size": 1,
}

# All available configurations
ALL_CONFIGS = {
    "NIFTY50_5MIN": NIFTY50_5MIN,
    "NIFTY50_1MIN": NIFTY50_1MIN,
    "BANKNIFTY_5MIN": BANKNIFTY_5MIN,
}

# Default configuration
DEFAULT_CONFIG = NIFTY50_5MIN
