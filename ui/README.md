# 🎯 Log-Fib Strategy Visualizer

Interactive TradingView-style chart visualizer for the Log-Fib Geometric Scalper strategy.

## 🚀 Quick Start

### Option 1: Python HTTP Server (Recommended)

```bash
cd /home/palbot/Projects/log-fib-scalper
source .venv/bin/activate
python -m http.server 8080
```

Then open: **http://localhost:8080/ui/visualizer.html**

### Option 2: Direct File Open

Some browsers allow opening the HTML file directly:
```bash
firefox ui/visualizer.html
# or
google-chrome ui/visualizer.html
```

Note: Direct file access may have CORS restrictions for loading CSV data.

---

## 📊 Features

### Interactive Chart
- **OHLC Candlestick Chart** - TradingView-style lightweight charts
- **Swing Point Markers** - Visual indicators for detected swing highs/lows
- **Trade Entry Markers** - LONG (blue ↑) and SHORT (purple ↓) entry points
- **Projection Lines** - Visualize the calculated entry/TP/SL levels

### Statistics Dashboard
- Win Rate %
- Profit Factor
- Total Trades
- Total P&L
- Average P&L per Trade
- Best Win Streak

### Configuration Panel
Customize strategy parameters in real-time:
- Lookback period (bars)
- Log-Fib multiplier
- Entry ratio (Fib retracement)
- Take profit (Fib extension)
- Stop loss (Fib extension)

### Trade History Table
- Last 50 trades with entry/exit details
- P&L per trade
- Win/Loss indicators
- Trade type (LONG/SHORT)

---

## 🎨 Chart Legend

| Symbol | Meaning |
|--------|---------|
| 🕯️ Green Candle | Bullish (close > open) |
| 🕯️ Red Candle | Bearish (close < open) |
| ⬇️ Red Arrow (SH) | Swing High detected |
| ⬆️ Green Arrow (SL) | Swing Low detected |
| ⬆️ Blue Arrow (L) | LONG entry signal |
| ⬇️ Purple Arrow (S) | SHORT entry signal |
| ┄┄ Dashed Lines | Projected entry levels |

---

## 📁 Data Files

The visualizer loads data from:

| Instrument | File Path |
|------------|-----------|
| Silver (XAGUSD) | `data/OANDA_XAGUSD5.csv` |
| Gold (XAUUSD) | `data/OANDA_XAUUSD5.csv` |
| Nifty50 | `zerodha_data/NIFTY_50_5minute_*.csv` |

---

## ⚙️ Pre-configured Strategies

### Silver Best (99.37% WR)
```
Lookback: 6
Multiplier: 0.5
Entry: 0.382
TP: 1.272
SL: 1.618
```

### Silver Alternative (98.85% WR)
```
Lookback: 6
Multiplier: 0.382
Entry: 0.382
TP: 1.272
SL: 1.0
```

### Gold Best (98.21% WR)
```
Lookback: 8
Multiplier: 0.618
Entry: 0.5
TP: 1.0
SL: 1.618
```

---

## 🛠️ Customization

### Add New Instruments

1. Place CSV file in `data/` or `zerodha_data/` folder
2. CSV format must have columns: `time,open,high,low,close`
3. Add option to `instrumentSelect` dropdown in HTML
4. Add file path mapping in `loadData()` function

### Add New Pre-sets

1. Add `<option>` to `configSelect` dropdown
2. Add config values in `loadData()` function
3. Update documentation above

---

## 📷 Export Chart

Click the **Export Chart** button to download the chart as PNG.

Note: Requires `html2canvas` library or use system screenshot tool.

---

## 🔧 Troubleshooting

### Chart not loading data
- Ensure you're running from project root directory
- Check browser console for CORS errors
- Use Python HTTP server instead of direct file open

### Wrong time format
- CSV timestamps should be ISO format or parseable by JavaScript Date
- Timezone offsets are automatically handled

### Chart appears empty
- Check that CSV has valid OHLC data
- Verify lookback period isn't larger than data size
- Try different instrument/config combination

---

## 📚 Technology Stack

- **Charting Library**: [Lightweight Charts](https://github.com/tradingview/lightweight-charts) by TradingView
- **Styling**: Custom CSS with GitHub Dark theme
- **Data Processing**: Pure JavaScript (no external dependencies)
- **Backtest Engine**: Ported from Python to JavaScript

---

## 🎯 Strategy Formula

The visualizer implements the exact Log-Fib formula:

```javascript
// Effective Range Calculation
effective_range = log10(pivot_price) * |pivot_price - anchor_price| * multiplier * 4

// LONG Setup
entry = swing_low + (entry_ratio * effective_range)
take_profit = swing_low + (tp_ratio * effective_range)
stop_loss = swing_low - (sl_ratio * effective_range)

// SHORT Setup
entry = swing_high - (entry_ratio * effective_range)
take_profit = swing_high - (tp_ratio * effective_range)
stop_loss = swing_high + (sl_ratio * effective_range)
```

Where:
- `pivot_price` = Swing high or low
- `anchor_price` = Opposite extreme of the same bar
- `multiplier` = Log-Fib scaling factor (0.382 - 0.786)
- `entry_ratio` = Fibonacci retracement for entry (0.382 - 0.786)
- `tp_ratio` = Fibonacci extension for target (1.0 - 1.618)
- `sl_ratio` = Fibonacci extension for stop (1.0 - 1.618)

---

## 📄 License

Part of the Log-Fib Scalper project - For personal trading use only.
