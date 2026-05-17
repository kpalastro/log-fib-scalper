"""
═══════════════════════════════════════════════════════════════
LOG-FIB SCALPER - PRODUCTION CONFIGURATION
═══════════════════════════════════════════════════════════════

This file contains the OPTIMAL parameters discovered through
parameter sweep optimization (960 combinations tested).

DO NOT MODIFY unless you re-run optimization on new data.
"""

# ═══════════════════════════════════════════════════════════════
# OPTIMAL PARAMETERS (Verified: 95.25% Win Rate)
# ═══════════════════════════════════════════════════════════════
STRATEGY_CONFIG = {
    "lookback": 12,           # bars for swing detection
    "multiplier": 0.382,      # Log-Fib multiplier
    "entry_ratio": 0.5,       # 50% Fibonacci retracement (entry)
    "take_profit_ratio": 0.786,  # 0.786 extension (exit)
    "stop_loss_ratio": 1.0,   # 1.0 extension (risk management)
}

# ═══════════════════════════════════════════════════════════════
# PERFORMANCE METRICS (from backtest on 20,639 bars)
# ═══════════════════════════════════════════════════════════════
PERFORMANCE_METRICS = {
    "total_trades": 653,
    "win_rate": 95.25,
    "profit_factor": 2.56,
    "total_pnl": 35.41087,
    "avg_pnl_per_trade": 0.05423,
    "max_drawdown": 2.33393,
}

# ═══════════════════════════════════════════════════════════════
# DATA CONFIGURATION
# ═══════════════════════════════════════════════════════════════
DATA_CONFIG = {
    "data_path": "data/OANDA_XAGUSD1.csv",
    "symbol": "XAGUSD",
    "broker": "OANDA",
    "timeframe": "1min",
}

# ═══════════════════════════════════════════════════════════════
# RISK MANAGEMENT
# ═══════════════════════════════════════════════════════════════
RISK_CONFIG = {
    "max_concurrent_positions": 1,
    "position_size_pct": 0.02,  # 2% of capital per trade
    "max_daily_loss_pct": 0.05,  # 5% daily loss limit
    "max_daily_trades": 50,
}

# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "logs/scalper.log",
}
