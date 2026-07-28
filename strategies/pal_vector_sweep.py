"""
Pal Vector Hybrid - Parameter Sweep
====================================

Optimize vector lookback and confluence threshold for maximum profitability.

Tests:
- Vector lookback: 20, 30, 40, 50, 60
- Confluence threshold: 40, 50, 60, 70
- Total: 20 configurations per instrument

Saves top 5 configs to JSON.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import json
from itertools import product
from strategies.pal_vector_hybrid import VectorLogFibHybrid, HybridBacktester, load_data

# Config ranges
VECTOR_LOOKBACKS = [20, 30, 40, 50, 60]
CONFLUENCE_THRESHOLDS = [40, 50, 60, 70]

# Data paths
SILVER_DATA = '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv'
GOLD_DATA = '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv'


def run_sweep(instrument: str, csv_path: str) -> list:
    """Run parameter sweep for one instrument."""
    print(f"\n{'=' * 80}")
    print(f"SWEEP: {instrument.upper()}")
    print(f"{'=' * 80}")
    
    data = load_data(csv_path)
    print(f"📈 Bars: {len(data):,} | Range: {data['datetime'].iloc[0].date()} → {data['datetime'].iloc[-1].date()}")
    
    results = []
    
    for vector_lb, conf_thresh in product(VECTOR_LOOKBACKS, CONFLUENCE_THRESHOLDS):
        # Modify strategy config temporarily
        strategy = VectorLogFibHybrid(instrument=instrument)
        strategy.vector_lb = vector_lb
        
        backtester = HybridBacktester(initial_capital=100000)
        
        # Run backtest
        trades = []
        capital = 100000
        position = None
        warmup = max(strategy.vector_lb, strategy.logfib_config['lookback']) + 10
        
        for i in range(warmup, len(data)):
            analysis = strategy.analyze(data, i)
            current_price = data['close'].iloc[i]
            timestamp = data['datetime'].iloc[i]
            
            # Entry (with confluence threshold)
            if position is None and analysis['signal'] == 'ENTER' and analysis['confluence'] >= conf_thresh:
                logfib = analysis['logfib']
                size = capital * 0.1 / current_price
                
                position = {
                    'direction': analysis['direction'],
                    'entry_price': logfib['entry'],
                    'size': size,
                    'tp': logfib['tp'],
                    'sl': logfib['sl'],
                    'entry_time': timestamp,
                    'confluence': analysis['confluence'],
                }
            
            # Exit
            elif position is not None:
                pnl = 0
                exit_reason = None
                exit_price = 0
                
                if position['direction'] == 'LONG':
                    if data['high'].iloc[i] >= position['tp']:
                        exit_price = position['tp']
                        pnl = (exit_price - position['entry_price']) * position['size']
                        exit_reason = 'TP'
                    elif data['low'].iloc[i] <= position['sl']:
                        exit_price = position['sl']
                        pnl = (exit_price - position['entry_price']) * position['size']
                        exit_reason = 'SL'
                else:
                    if data['low'].iloc[i] <= position['tp']:
                        exit_price = position['tp']
                        pnl = (position['entry_price'] - exit_price) * position['size']
                        exit_reason = 'TP'
                    elif data['high'].iloc[i] >= position['sl']:
                        exit_price = position['sl']
                        pnl = (position['entry_price'] - exit_price) * position['size']
                        exit_reason = 'SL'
                
                if exit_reason:
                    trades.append({'pnl': pnl, 'exit_reason': exit_reason})
                    capital += pnl
                    position = None
        
        # Calculate metrics
        if trades:
            wins = [t for t in trades if t['pnl'] > 0]
            losses = [t for t in trades if t['pnl'] <= 0]
            
            total_pnl = sum(t['pnl'] for t in trades)
            gross_profit = sum(t['pnl'] for t in wins)
            gross_loss = abs(sum(t['pnl'] for t in losses))
            
            results.append({
                'vector_lookback': vector_lb,
                'confluence_threshold': conf_thresh,
                'total_trades': len(trades),
                'wins': len(wins),
                'losses': len(losses),
                'win_rate': len(wins) / len(trades) * 100,
                'total_pnl': total_pnl,
                'return_pct': (capital - 100000) / 100000 * 100,
                'profit_factor': gross_profit / gross_loss if gross_loss > 0 else float('inf'),
                'avg_pnl_per_trade': total_pnl / len(trades) if trades else 0,
            })
        
        print(f"  LB={vector_lb:2d}, Conf={conf_thresh:2d} → {len(trades):2d} trades, WR={len(wins)/len(trades)*100:5.1f}%, P&L=${total_pnl:8.2f}, PF={gross_profit/gross_loss if gross_loss > 0 else float('inf'):6.2f}")
    
    # Sort by profit factor, then by total P&L
    results.sort(key=lambda x: (x['profit_factor'], x['total_pnl']), reverse=True)
    
    return results


if __name__ == '__main__':
    print("=" * 80)
    print("PAL VECTOR HYBRID - PARAMETER SWEEP")
    print("=" * 80)
    
    all_results = {}
    
    for instrument, csv_path in [('silver', SILVER_DATA), ('gold', GOLD_DATA)]:
        results = run_sweep(instrument, csv_path)
        all_results[instrument] = results
        
        # Save top 5
        top_5 = results[:5]
        output_file = f'/home/palbot/Projects/log-fib-scalper/sweep_results_{instrument}.json'
        
        with open(output_file, 'w') as f:
            json.dump({
                'instrument': instrument,
                'sweep_date': pd.Timestamp.now().isoformat(),
                'top_configs': top_5,
                'all_results': results,
            }, f, indent=2, default=str)
        
        print(f"\n🏆 TOP 5 CONFIGS - {instrument.upper()}")
        print("-" * 80)
        for i, config in enumerate(top_5, 1):
            print(f"{i}. LB={config['vector_lookback']:2d}, Conf={config['confluence_threshold']:2d} | "
                  f"Trades={config['total_trades']:2d}, WR={config['win_rate']:5.1f}%, "
                  f"P&L=${config['total_pnl']:8.2f}, PF={config['profit_factor']:6.2f}")
    
    print("\n" + "=" * 80)
    print("💾 Results saved to:")
    print(f"   - /home/palbot/Projects/log-fib-scalper/sweep_results_silver.json")
    print(f"   - /home/palbot/Projects/log-fib-scalper/sweep_results_gold.json")
    print("=" * 80)
