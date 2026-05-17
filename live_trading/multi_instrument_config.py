"""
═══════════════════════════════════════════════════════════════
MULTI-INSTRUMENT STRATEGY CONFIGURATIONS
═══════════════════════════════════════════════════════════════

Optimal parameters for each instrument/timeframe combination.
Discovered through exhaustive parameter sweep optimization.
"""

# ═══════════════════════════════════════════════════════════════
# SILVER (XAGUSD) 1-MINUTE
# ═══════════════════════════════════════════════════════════════
XAGUSD_1MIN = {
    "instrument": "XAGUSD",
    "timeframe": "1min",
    "ig_epic": "IX.D.SILVER.IPV",
    "config": {
        "lookback": 12,
        "multiplier": 0.382,
        "entry_ratio": 0.5,
        "take_profit_ratio": 0.786,
        "stop_loss_ratio": 1.0,
    },
    "performance": {
        "win_rate": 95.25,
        "profit_factor": 2.56,
        "total_pnl": 35.41,
        "total_trades": 653,
        "avg_pnl_per_trade": 0.054,
        "max_drawdown": 2.33,
    }
}

# ═══════════════════════════════════════════════════════════════
# GOLD (XAUUSD) 5-MINUTE ⭐ RECOMMENDED
# ═══════════════════════════════════════════════════════════════
XAUUSD_5MIN = {
    "instrument": "XAUUSD",
    "timeframe": "5min",
    "ig_epic": "IX.D.GOLD.IPV",
    "config": {
        "lookback": 10,
        "multiplier": 0.786,
        "entry_ratio": 0.5,
        "take_profit_ratio": 0.618,
        "stop_loss_ratio": 1.414,
    },
    "performance": {
        "win_rate": 98.43,
        "profit_factor": 4.45,
        "total_pnl": 1558.08,
        "total_trades": 191,
        "avg_pnl_per_trade": 8.16,
        "max_drawdown": 253.71,
    }
}

# ═══════════════════════════════════════════════════════════════
# GOLD (XAUUSD) 1-MINUTE
# ═══════════════════════════════════════════════════════════════
XAUUSD_1MIN = {
    "instrument": "XAUUSD",
    "timeframe": "1min",
    "ig_epic": "IX.D.GOLD.IPV",
    "config": {
        "lookback": 10,
        "multiplier": 0.786,
        "entry_ratio": 0.618,
        "take_profit_ratio": 1.0,
        "stop_loss_ratio": 1.0,
    },
    "performance": {
        "win_rate": 93.48,
        "profit_factor": 3.27,
        "total_pnl": 523.40,
        "total_trades": 92,
        "avg_pnl_per_trade": 5.69,
        "max_drawdown": 58.20,
    }
}

# ═══════════════════════════════════════════════════════════════
# ALL CONFIGURATIONS (for easy iteration)
# ═══════════════════════════════════════════════════════════════
ALL_CONFIGS = {
    "XAGUSD_1MIN": XAGUSD_1MIN,
    "XAUUSD_5MIN": XAUUSD_5MIN,  # ⭐ Best overall
    "XAUUSD_1MIN": XAUUSD_1MIN,
}

# Default configuration (Gold 5-min - highest profit factor)
DEFAULT_CONFIG = XAUUSD_5MIN

# ═══════════════════════════════════════════════════════════════
# CRYPTO CONFIGURATIONS (Gate.io)
# ═══════════════════════════════════════════════════════════════

# BITCOIN (BTCUSDT) 5-MINUTE ⭐ BEST CRYPTO
BTCUSDT_5MIN = {
    "instrument": "BTCUSDT",
    "timeframe": "5min",
    "gate_pair": "BTC_USDT",
    "config": {
        "lookback": 14,
        "multiplier": 0.786,
        "entry_ratio": 0.382,
        "take_profit_ratio": 1.0,
        "stop_loss_ratio": 1.414,
    },
    "performance": {
        "win_rate": 94.59,
        "profit_factor": 3.79,
        "total_pnl": 29047.02,
        "total_trades": 37,
        "avg_pnl_per_trade": 785.05,
        "max_drawdown": 7585.15,
    }
}

# ETHEREUM (ETHUSDT) 5-MINUTE - PLACEHOLDER
ETHUSDT_5MIN = {
    "instrument": "ETHUSDT",
    "timeframe": "5min",
    "gate_pair": "ETH_USDT",
    "config": {
        "lookback": 14,
        "multiplier": 0.786,
        "entry_ratio": 0.382,
        "take_profit_ratio": 1.0,
        "stop_loss_ratio": 1.414,
    },
    "performance": {
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "total_pnl": 0.0,
        "total_trades": 0,
        "avg_pnl_per_trade": 0.0,
        "max_drawdown": 0.0,
        "note": "Pending optimization - using BTC params as starting point"
    }
}

# RIPPLE (XRPUSDT) 5-MINUTE - PLACEHOLDER
XRPUSDT_5MIN = {
    "instrument": "XRPUSDT",
    "timeframe": "5min",
    "gate_pair": "XRP_USDT",
    "config": {
        "lookback": 14,
        "multiplier": 0.786,
        "entry_ratio": 0.382,
        "take_profit_ratio": 1.0,
        "stop_loss_ratio": 1.414,
    },
    "performance": {
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "total_pnl": 0.0,
        "total_trades": 0,
        "avg_pnl_per_trade": 0.0,
        "max_drawdown": 0.0,
        "note": "Pending optimization - using BTC params as starting point"
    }
}

# ═══════════════════════════════════════════════════════════════
# ALL CRYPTO CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════
CRYPTO_CONFIGS = {
    "BTCUSDT_5MIN": BTCUSDT_5MIN,
    "ETHUSDT_5MIN": ETHUSDT_5MIN,
    "XRPUSDT_5MIN": XRPUSDT_5MIN,
}

# ═══════════════════════════════════════════════════════════════
# ALL CONFIGURATIONS (UPDATED WITH CRYPTO)
# ═══════════════════════════════════════════════════════════════
ALL_CONFIGS = {
    "XAGUSD_1MIN": XAGUSD_1MIN,
    "XAUUSD_5MIN": XAUUSD_5MIN,
    "XAUUSD_1MIN": XAUUSD_1MIN,
    "BTCUSDT_5MIN": BTCUSDT_5MIN,
    "ETHUSDT_5MIN": ETHUSDT_5MIN,
    "XRPUSDT_5MIN": XRPUSDT_5MIN,
}
