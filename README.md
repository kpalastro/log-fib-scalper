# 🎯 Log-Fib Geometric Scalper

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Platform: Linux](https://img.shields.io/badge/platform-linux%20%7C%20macOS%20%7C%20WSL-lightgrey.svg)]()
[![Win Rate](https://img.shields.io/badge/win%20rate-95.25%25-brightgreen.svg)](#-performance-metrics)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./.github/CONTRIBUTING.md)

> **Production-Ready Algorithmic Trading Strategy** — A pure mathematical, geometric scalping strategy that identifies precise market tops and bottoms using logarithmic Fibonacci projections. **Zero lagging indicators.**

A pure mathematical, geometric scalping strategy that identifies precise market tops and bottoms using logarithmic Fibonacci projections — **zero lagging indicators**.

---

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| **Win Rate** | 95.25% |
| **Profit Factor** | 2.56 |
| **Total P&L** | +35.41 |
| **Total Trades** | 653 |
| **Max Drawdown** | 2.33 |
| **Avg P&L/Trade** | +0.054 |

*Backtested on 20,639 bars of XAGUSD (Silver) 1-minute data*

---

## 🧬 Strategy Philosophy

### Core Principles
1. **No Lagging Indicators** — No RSI, MACD, Bollinger Bands, or moving averages
2. **Pure Geometry** — Uses logarithmic price projections and Fibonacci ratios
3. **Anchored Swing Points** — Identifies structural highs/lows with anchored baselines
4. **Mathematical Precision** — Every level calculated from first principles

### The Formula

```python
# Top Projection (SHORT setups)
effective_range_top = log10(SwingHigh) × |SwingHigh - AnchoredLow| × multiplier × 4.0

# Bottom Projection (LONG setups)
effective_range_bot = log10(SwingLow) × |SwingLow - AnchoredHigh| × multiplier × 4.0

# Entry: 50% Fibonacci retracement
# Exit: 0.786 Fibonacci extension
# Stop: 1.0 Fibonacci extension
```

---

## 🏗️ Architecture

```
                          ┌──────────────────────────┐
                          │   Market Data (OHLCV)     │
                          │  IG · Zerodha · Yahoo ·   │
                          │  Gate.io · CSV            │
                          └────────────┬─────────────┘
                                       │
                          ┌────────────▼─────────────┐
                          │   data/ fetcher layer    │
                          │  ig_data_fetcher.py      │
                          │  zerodha_data_fetcher.py │
                          │  yahoo_data_fetcher.py   │
                          └────────────┬─────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
   ┌──────────▼──────────┐  ┌──────────▼──────────┐  ┌──────────▼──────────┐
   │  Log-Fib Scalper     │  │  Pal Vector Scalper │  │  Geometric Confluence│
   │  (Core Strategy)     │  │  (Velocity Vectors) │  │  (Fib+Gann+Markov)  │
   │  scripts/            │  │  strategies/        │  │  strategies/        │
   └──────────┬──────────┘  └──────────┬──────────┘  └──────────┬──────────┘
              │                        │                        │
              └────────────────────────┼────────────────────────┘
                                       │
                          ┌────────────▼─────────────┐
                          │  Live Trading Agent V2   │
                          │  live_trading/           │
                          │  · multi-instrument      │
                          │  · risk-managed          │
                          │  · order execution       │
                          └────────────┬─────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
   ┌──────────▼──────────┐  ┌──────────▼──────────┐  ┌──────────▼──────────┐
   │  Scanner / Alerts   │  │  UI Visualizer      │  │  Backtest Engine    │
   │  scanner/           │  │  ui/ (HTML/JS)      │  │  scripts/ + walk-fwd│
   └─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

**Data flow:** Market data → strategy engine → live agent (risk-managed execution) → broker API. The scanner watches for setups; the UI renders signals on a TradingView-style chart; the backtest engine validates each strategy on historical data, including walk-forward analysis.

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/kpalastro/log-fib-scalper.git
cd log-fib-scalper
```

### 2. Install Dependencies
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> The core scalper uses only Python stdlib (`csv`, `math`, `os`, `datetime`). Optional packages enable live trading (`requests`, `python-dotenv`), advanced analytics (`pandas`, `numpy`, `matplotlib`), and broker APIs.

### 3. Add Your Data
Place your OHLCV CSV file in the `data/` folder:
```
data/
└── OANDA_XAGUSD1.csv
```

**Required CSV columns:** `time`, `open`, `high`, `low`, `close`, `Volume`

### 4. Run the Scalper
```bash
python scripts/log_fib_scalper_production.py
```

---

## 📁 Project Structure

```
log-fib-scalper/
├── config.py                         # Production configuration (optimal params)
├── requirements.txt                  # Python dependencies
├── README.md                         # This file
├── LICENSE                           # MIT License
├── .gitignore                        # Git ignore rules (covers .env*, venv, creds)
├── Dockerfile / docker-compose.yml   # Containerized deployment
├── deploy.sh / *.service             # Systemd + deploy scripts
│
├── scripts/                          # 🎯 Core strategy + backtesting
│   ├── log_fib_scalper_production.py #    MAIN PRODUCTION SCRIPT
│   ├── log_fib_projection.py         #    Core formula implementation
│   ├── backtest_engine_v2.py         #    Backtesting engine
│   ├── parameter_sweep_v2.py         #    Parameter optimization (960 combos)
│   ├── log_fib_mtf_optimizer.py      #    Multi-timeframe optimizer
│   ├── verify_configurations.py      #    Configuration verifier
│   └── *.json                         #    Optimization results
│
├── strategies/                       # 🧬 Advanced strategy variants
│   ├── geometric_confluence_scalper.py  # Fib + Gann + Markov confluence
│   ├── pal_vector_scalper.py         #    Demand/supply velocity vectors
│   ├── pal_vector_hybrid.py          #    Hybrid Log-Fib + Pal Vector
│   ├── pal_vector_60day.py           #    60-day extended backtest
│   ├── pal_vector_sweep.py           #    Parameter sweep
│   └── pal_vector_walkforward.py     #    Walk-forward validation
│
├── live_trading/                     # 🚀 Live broker integration
│   ├── live_agent.py                 #    Live Trading Agent V2
│   ├── ig_client.py                  #    IG Markets API client
│   ├── neo_client.py                 #    Kotak Neo broker client
│   ├── zerodha_data_fetcher.py       #    Zerodha Kite data fetcher
│   ├── nifty_live_agent.py           #    NIFTY live agent
│   ├── multi_instrument_config.py    #    Multi-instrument configs
│   ├── backtest_*.py                 #    Backtest variants (30min, 5min, 2y)
│   ├── walk_forward_*.py             #    Walk-forward backtests
│   ├── crypto/                       #    Crypto sub-agent (Gate.io)
│   │   ├── crypto_agent.py
│   │   └── gate_client.py
│   ├── .env.example                  #    Credential template (safe to commit)
│   └── LIVE_TRADING_README.md        #    Live trading setup guide
│
├── scanner/                          # 📡 Real-time signal scanner
│   ├── real_time_scanner.py          #    Live market scanner
│   ├── scalping_scanner.py           #    Scalping signal scanner
│   ├── nifty_scanner.py              #    NIFTY scanner
│   └── check_alerts.py               #    Alert verification
│
├── analysis/                         # 🔬 Strategy research
│   ├── deep_swing_research.py        #    Swing structure research
│   ├── nifty_geometric_validation.py #    NIFTY geometric validation
│   ├── validate_higher_tf.py         #    Higher-timeframe validation
│   └── swing_relationships.py        #    Swing relationship analysis
│
├── discovery/                        # 🔍 Parameter discovery
│   ├── sweep_v1.py                   #    Initial sweep
│   └── walk_forward_validation.py    #    Walk-forward validation
│
├── data/                             # 📊 Market data + fetchers (data not committed)
│   ├── ig_data_fetcher.py            #    IG data fetcher
│   ├── yahoo_data_fetcher.py         #    Yahoo Finance fetcher
│   └── yahoo_live_fetcher.py         #    Yahoo live fetcher
│
├── mcp/                              # 🔌 MCP integration
│   ├── market_data_server.py         #    MCP market data server
│   └── setup-zerodha-*.sh            #    Zerodha MCP setup
│
├── ui/                               # 📈 Strategy visualizer
│   ├── pal_vector_server.py          #    Visualizer backend
│   ├── pal_vector_visualizer.html    #    TradingView-style chart
│   └── visualizer.html               #    Main visualizer
│
├── sample_strategies/                # 📝 Reference Pine Script strategies
├── llms/                             # 🤖 AI model configs
└── logs/                             # 📋 Runtime logs (created on run)
```

---

## ⚙️ Configuration

Edit `config.py` to adjust parameters:

```python
STRATEGY_CONFIG = {
    "lookback": 12,           # Swing detection window
    "multiplier": 0.382,      # Log-Fib multiplier
    "entry_ratio": 0.5,       # Entry retracement level
    "take_profit_ratio": 0.786,  # Take profit extension
    "stop_loss_ratio": 1.0,   # Stop loss extension
}
```

**⚠️ Warning:** These parameters are optimized. Only modify after re-running `parameter_sweep_v2.py` on your specific dataset.

---

## 📈 Strategy Variants

| Strategy | File | Concept |
|----------|------|---------|
| **Log-Fib Scalper** | `scripts/log_fib_scalper_production.py` | Logarithmic Fibonacci projections (core) |
| **Geometric Confluence** | `strategies/geometric_confluence_scalper.py` | Fib retracement + Gann squares + Markov patterns |
| **Pal Vector Scalper** | `strategies/pal_vector_scalper.py` | Demand/supply velocity vectors from Pine Script |
| **Pal Vector Hybrid** | `strategies/pal_vector_hybrid.py` | Hybrid Log-Fib + Pal Vector confluence |

See `PAL_VECTOR_README.md` and `PAL_VECTOR_IMPLEMENTATION.md` for the Pal Vector lineage.

---

## 🚀 Live Trading

The live agent supports multi-instrument trading with broker integrations:

| Broker | Instruments | Client |
|--------|-----------|--------|
| **IG Markets** | XAGUSD (Silver), XAUUSD (Gold) | `live_trading/ig_client.py` |
| **Kotak Neo** | NIFTY, BANKNIFTY | `live_trading/neo_client.py` |
| **Zerodha Kite** | NIFTY, BANKNIFTY | `live_trading/zerodha_data_fetcher.py` |
| **Gate.io** | BTC, ETH (crypto) | `live_trading/crypto/gate_client.py` |

### Setup
```bash
cd live_trading
cp .env.example .env       # Template (safe — no secrets)
# Edit .env with YOUR credentials — NEVER commit .env
```

See `live_trading/LIVE_TRADING_README.md` for full setup. **Start with a DEMO account.**

> 🔒 **Credential safety:** `.env`, `.env.neo`, `.env.zerodha`, and all `.env.*` variants are gitignored. Only `.env.example` (placeholders) is tracked.

---

## 🔬 Optimization History

This strategy was optimized using a **multi-agent Quant Squad** approach:

1. **Data Engineer Agent** — Validated and prepared 20,639 bars of XAGUSD data
2. **Statistician Agent** — Implemented geometric pattern detection
3. **Strategist Agent** — Formulated trading rules
4. **Auditor Agent** — Backtested and validated performance

**Total Combinations Tested:** 960  
**Profitable Configurations Found:** 717  
**Best Configuration Selected:** 95.25% win rate

Walk-forward validation results are in `walk_forward_*.json` and `scripts/verification_report.json`.

---

## 📈 Trading Signals

The scalper generates signals in this format:

```
Signal #1: SHORT ↓
  Swing Time:    2026-05-15T14:54:00-04:00
  Swing Price:   77.05300
  Entry Zone:    76.96219
  Take Profit:   76.91024
  Stop Loss:     77.23463
```

---

## 🛡️ Risk Management

Built-in risk controls:
- Maximum 1 concurrent position
- 2% position sizing per trade
- 5% daily loss limit
- Maximum 50 trades per day

---

## 📝 License

MIT License — See [LICENSE](./LICENSE)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing`)
3. Run tests: `python scripts/backtest_engine_v2.py`
4. Submit a pull request

---

## 📞 Support

For issues or questions, open a [GitHub issue](https://github.com/kpalastro/log-fib-scalper/issues).

---

*Built with ❤️ by Hermes Quant Squad · Author: Kul Deep Pal ([@kpalastro](https://github.com/kpalastro))*
