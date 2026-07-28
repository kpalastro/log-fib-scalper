# 🎯 Pal Vector + Log-Fib - 60-Day Backtest & Walk-Forward Results

**Date:** 2026-05-20  
**Data:** 60 days (13,537 Silver bars, 13,550 Gold bars)  
**Period:** March 10 - May 19, 2026

---

## 📊 Executive Summary

**Result:** ❌ Strategy NOT Walk-Forward Validated

Despite promising 1-month results (100% WR), the 60-day extended backtest and 5-fold walk-forward validation reveal:

1. **Silver:** 33% WR, -1.20% return, PF 0.46 (losing strategy)
2. **Gold:** 100% WR but only 1 trade in 60 days (insufficient data)
3. **Walk-Forward:** 0/12 configs validated for Silver, 0/12 for Gold

**Root Cause:** The hybrid is **too conservative** - produces 1-3 trades in 60 days, making results statistically meaningless.

---

## 📈 60-Day Extended Backtest Results

### Configuration Tested
```python
# Silver
Vector Lookback: 20
Confluence: 50
Log-Fib: LB=6, Mult=0.5, Entry=0.382, TP=1.272, SL=1.618

# Gold
Vector Lookback: 30
Confluence: 50
Log-Fib: LB=8, Mult=0.618, Entry=0.5, TP=1.0, SL=1.618
```

### Performance Metrics

| Metric | Silver | Gold |
|--------|--------|------|
| **Total Trades** | 3 | 1 |
| **Win Rate** | 33.33% | 100.00% |
| **Total P&L** | -$1,203.23 | +$212.46 |
| **Return** | -1.20% | +0.21% |
| **Profit Factor** | 0.46 | ∞ |
| **Sharpe Ratio** | -0.08 | 0.14 |
| **Max Drawdown** | 2.23% | 0.00% |
| **Avg Trade Duration** | 328 hours | 83 hours |

### Trade Log - Silver
| # | Date | Direction | Entry | Exit | P&L | Confluence | Reason |
|---|------|-----------|-------|------|-----|------------|--------|
| 1 | 2026-03-10 | LONG | 89.8575 | 84.6350 | -$586.93 | 80 | SL |
| 2 | 2026-03-11 | LONG | 87.2494 | 73.1427 | -$1,642.91 | 80 | SL |
| 3 | 2026-03-19 | LONG | 75.9490 | 83.6352 | +$1,026.61 | 80 | TP |

### Trade Log - Gold
| # | Date | Direction | Entry | Exit | P&L | Confluence | Reason |
|---|------|-----------|-------|------|-----|------------|--------|
| 1 | 2026-03-10 | SHORT | 5081.09 | 4970.88 | +$212.46 | 80 | TP |

### Key Observations

**Silver Issues:**
- ❌ 2 consecutive losses early in test period
- ❌ Largest loss (-$1,642) was 1.6x larger than largest win (+$1,026)
- ❌ All trades were LONG during a **downtrending market** ($88 → $74)
- ❌ Vector trend filter failed to identify bearish regime

**Gold Issues:**
- ⚠️ Only 1 trade in 60 days (statistically insignificant)
- ✅ That trade was profitable (+$212)
- ⚠️ Strategy too conservative to generate sufficient trades

---

## 🔬 Walk-Forward Validation (5 Folds)

### Methodology
- **Folds:** 5 (14 days each)
- **Configs Tested:** 12 (4 vector LB × 3 confluence thresholds)
- **Validation Criteria:**
  - ✅ 5/5 folds profitable
  - ✅ Aggregate WR ≥ 90%
  - ✅ Aggregate PF ≥ 2.0

### Results Summary

| Instrument | Configs Tested | Validated | Best Config | Best WR | Best PF |
|------------|----------------|-----------|-------------|---------|---------|
| **Silver** | 12 | **0** | LB=50, Conf=60 | 72.7% | 1.98 |
| **Gold** | 12 | **0** | LB=20-30, Conf=40-60 | 100% | ∞ |

### Silver - Best Performing Config (LB=50, Conf=60)
- **Profitable Folds:** 4/5 ❌ (fails validation)
- **Aggregate WR:** 72.7% (below 90% threshold)
- **Aggregate PF:** 1.98 (below 2.0 threshold)
- **Total Trades:** 11 across all folds

### Gold - Best Performing Config (LB=30, Conf=50)
- **Profitable Folds:** 3/5 ❌ (fails validation)
- **Aggregate WR:** 100% ✅
- **Aggregate PF:** ∞ ✅
- **Total Trades:** 3 across all folds (insufficient)

### Fold-by-Fold Breakdown (Silver, LB=50, Conf=60)

| Fold | Date Range | Trades | WR | P&L | Status |
|------|------------|--------|----|-----|--------|
| 0 | 2026-03-10 → 2026-03-24 | 3 | 66.7% | +$234 | ✅ Profit |
| 1 | 2026-03-24 → 2026-04-07 | 2 | 100% | +$567 | ✅ Profit |
| 2 | 2026-04-07 → 2026-04-21 | 2 | 50% | -$123 | ❌ Loss |
| 3 | 2026-04-21 → 2026-05-05 | 2 | 100% | +$445 | ✅ Profit |
| 4 | 2026-05-05 → 2026-05-19 | 2 | 50% | +$89 | ✅ Profit |

**Issue:** Fold 2 lost money → fails 5/5 folds requirement

---

## 🧠 Root Cause Analysis

### 1. **Strategy Too Conservative**
- 1-3 trades in 60 days = 1 trade per 20-60 days
- **Problem:** Not enough data points for statistical significance
- **Cause:** High confluence threshold (50) + strict vector filter

### 2. **Vector Trend Filter Fails in Strong Trends**
- Silver dropped from $88 to $74 (-16%) over 60 days
- Vector filter kept generating LONG signals (counter-trend)
- **Problem:** Vector lookback (20-30 bars = 1.5-2.5 hours) too short for macro trend

### 3. **Log-Fib Configs Optimized for Mean Reversion, Not Trend Following**
- Validated Log-Fib configs (99% WR) were for **range-bound** markets
- Current implementation uses them for **trend-following**
- **Mismatch:** Entry/exit levels designed for bounces, not breakouts

### 4. **No Higher-Timeframe Confirmation**
- 5-min signals not filtered by 1H/4H trend
- **Result:** Taking counter-trend trades on higher TF

---

## 💡 Recommendations

### Option A: Abandon Hybrid, Use Pure Log-Fib
**Rationale:** The validated Log-Fib configs (99.37% Silver, 98.21% Gold) already work. Adding vector filter reduces trade frequency without improving quality.

**Action:**
```python
# Revert to pure Log-Fib with validated configs
# Silver: LB=6, Mult=0.5, Entry=0.382, TP=1.272, SL=1.618
# Gold: LB=8, Mult=0.618, Entry=0.5, TP=1.0, SL=1.618
```

### Option B: Optimize Hybrid for More Trades
**Changes:**
1. Lower confluence threshold: 50 → 30
2. Shorter vector lookback: 20 → 10
3. Add higher-TF trend filter (1H/4H)

**Expected:** 10-20 trades in 60 days (statistically meaningful)

### Option C: Use Vectors for Exit Management Only
**Architecture:**
- Log-Fib for entry (validated 99% WR configs)
- Vector levels for **dynamic TP/SL adjustment**
- Vector trend for **position sizing** (larger in trend direction)

### Option D: Focus on Gold Only
**Rationale:** Gold showed 100% WR (albeit 1 trade). Silver failed consistently.

**Risk:** 1 trade in 60 days is not statistically significant

---

## 📁 Files Generated

### Backtest Results
- `extended_backtest_silver_60day.json` - Full Silver backtest
- `extended_backtest_gold_60day.json` - Full Gold backtest
- `walkforward_results.json` - Walk-forward validation data

### Scripts
- `strategies/pal_vector_60day.py` - Extended backtest engine
- `strategies/pal_vector_walkforward.py` - Walk-forward validation
- `strategies/pal_vector_hybrid.py` - Hybrid strategy
- `strategies/pal_vector_sweep.py` - Parameter sweep

### Documentation
- `PAL_VECTOR_README.md` - User guide
- `PAL_VECTOR_IMPLEMENTATION.md` - Technical summary
- `PAL_VECTOR_60DAY_RESULTS.md` - This file

---

## 🎯 Final Verdict

**Status:** ❌ **NOT VALIDATED** - Do NOT use for live trading

**Reason:**
1. Too few trades (1-3 in 60 days)
2. Silver losing money (-1.20%, PF 0.46)
3. 0/12 configs passed walk-forward validation
4. Vector trend filter counter-productive in strong trends

**Recommendation:** 
- ✅ Use **pure Log-Fib** with validated configs (99.37% WR Silver)
- ❌ Do NOT use hybrid strategy in current form
- ⏳ If pursuing hybrid: redesign for more trades + higher-TF confirmation

---

## 📊 Comparison: 1-Month vs 60-Day Results

| Metric | 1-Month Silver | 60-Day Silver | 1-Month Gold | 60-Day Gold |
|--------|----------------|---------------|--------------|-------------|
| **Trades** | 3 | 3 | 1 | 1 |
| **Win Rate** | 100% | 33.33% | 100% | 100% |
| **P&L** | +$2,056 | -$1,203 | +$156 | +$212 |
| **Return** | +2.06% | -1.20% | +0.16% | +0.21% |
| **Profit Factor** | ∞ | 0.46 | ∞ | ∞ |

**Key Insight:** 1-month results were **cherry-picked** (favorable market regime). 60-day test reveals true performance.

---

*Created: 2026-05-20 | Analysis: Hermes Quant Squad | Status: Honest Assessment*
