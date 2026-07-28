"""
Pal Vector Hybrid - Walk-Forward Validation (5 Folds)
======================================================

Split 60-day data into 5 folds (12 days each).
Validate each configuration across all folds to ensure NOT overfit.

Criteria for VALIDATED config:
- 5/5 folds profitable
- Aggregate win rate ≥ 90%
- Aggregate profit factor ≥ 2.0

Usage:
    python pal_vector_walkforward.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from typing import Dict
from itertools import product
from strategies.pal_vector_hybrid import VectorLogFibHybrid, load_data

# Data paths
SILVER_DATA = '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv'
GOLD_DATA = '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv'

# Config ranges to test
VECTOR_LOOKBACKS = [20, 30, 40, 50]
CONFLUENCE_THRESHOLDS = [40, 50, 60]
NUM_FOLDS = 5


def run_fold(data: pd.DataFrame, fold_idx: int, fold_size: int,
             instrument: str, vector_lb: int, confluence_thresh: int) -> Dict:
    """Run backtest on single fold."""
    start_idx = fold_idx * fold_size
    end_idx = start_idx + fold_size
    
    fold_data = data.iloc[start_idx:end_idx].copy()
    
    if len(fold_data) < 100:
        return {'error': 'Insufficient data'}
    
    strategy = VectorLogFibHybrid(instrument=instrument)
    strategy.vector_lb = vector_lb
    
    trades = []
    capital = 100000
    position = None
    
    warmup = max(strategy.vector_lb, strategy.logfib_config['lookback']) + 10
    
    for i in range(warmup, len(fold_data)):
        analysis = strategy.analyze(fold_data, i)
        current_price = fold_data['close'].iloc[i]
        timestamp = fold_data['datetime'].iloc[i]
        
        # Entry
        if position is None and analysis['signal'] == 'ENTER' and analysis['confluence'] >= confluence_thresh:
            logfib = analysis['logfib']
            size = capital * 0.1 / current_price
            
            position = {
                'direction': analysis['direction'],
                'entry_price': logfib['entry'],
                'size': size,
                'tp': logfib['tp'],
                'sl': logfib['sl'],
                'entry_time': timestamp,
            }
        
        # Exit
        elif position is not None:
            pnl = 0
            exit_reason = None
            exit_price = 0
            
            if position['direction'] == 'LONG':
                if fold_data['high'].iloc[i] >= position['tp']:
                    exit_price = position['tp']
                    pnl = (exit_price - position['entry_price']) * position['size']
                    exit_reason = 'TP'
                elif fold_data['low'].iloc[i] <= position['sl']:
                    exit_price = position['sl']
                    pnl = (exit_price - position['entry_price']) * position['size']
                    exit_reason = 'SL'
            else:
                if fold_data['low'].iloc[i] <= position['tp']:
                    exit_price = position['tp']
                    pnl = (position['entry_price'] - exit_price) * position['size']
                    exit_reason = 'TP'
                elif fold_data['high'].iloc[i] >= position['sl']:
                    exit_price = position['sl']
                    pnl = (position['entry_price'] - exit_price) * position['size']
                    exit_reason = 'SL'
            
            if exit_reason:
                trades.append({'pnl': pnl, 'exit_reason': exit_reason})
                capital += pnl
                position = None
    
    if not trades:
        return {
            'fold': fold_idx,
            'trades': 0,
            'pnl': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'error': 'No trades',
        }
    
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    
    total_pnl = sum(t['pnl'] for t in trades)
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    
    return {
        'fold': fold_idx,
        'start_date': str(fold_data['datetime'].iloc[0]),
        'end_date': str(fold_data['datetime'].iloc[-1]),
        'trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': len(wins) / len(trades) * 100 if trades else 0,
        'total_pnl': total_pnl,
        'profit_factor': gross_profit / gross_loss if gross_loss > 0 else (float('inf') if gross_profit > 0 else 0),
        'return_pct': (capital - 100000) / 100000 * 100,
    }


def run_walkforward(data: pd.DataFrame, instrument: str,
                   vector_lb: int, confluence_thresh: int) -> Dict:
    """Run walk-forward validation across all folds."""
    fold_size = len(data) // NUM_FOLDS
    
    fold_results = []
    for fold_idx in range(NUM_FOLDS):
        result = run_fold(data, fold_idx, fold_size, instrument, vector_lb, confluence_thresh)
        fold_results.append(result)
    
    # Aggregate metrics
    total_trades = sum(r.get('trades', 0) for r in fold_results)
    total_wins = sum(r.get('wins', 0) for r in fold_results)
    total_pnl = sum(r.get('total_pnl', 0) for r in fold_results)
    profitable_folds = sum(1 for r in fold_results if r.get('total_pnl', 0) > 0)
    
    # Calculate aggregate profit factor
    all_gross_profit = 0
    all_gross_loss = 0
    for r in fold_results:
        if r['trades'] > 0:
            # Reconstruct from win_rate and pnl
            wins_pnl = r['total_pnl'] * (r['win_rate'] / 100) if r['total_pnl'] != 0 else 0
            losses_pnl = r['total_pnl'] * (1 - r['win_rate'] / 100) if r['total_pnl'] != 0 else 0
            if r['total_pnl'] > 0:
                all_gross_profit += abs(wins_pnl)
            else:
                all_gross_loss += abs(losses_pnl)
    
    aggregate_pf = all_gross_profit / all_gross_loss if all_gross_loss > 0 else (float('inf') if all_gross_profit > 0 else 0)
    
    aggregate_wr = total_wins / total_trades * 100 if total_trades > 0 else 0
    
    # Validation status
    is_validated = (
        profitable_folds == NUM_FOLDS and  # 5/5 folds profitable
        aggregate_wr >= 90 and  # Aggregate WR ≥ 90%
        aggregate_pf >= 2.0  # Aggregate PF ≥ 2.0
    )
    
    return {
        'config': {
            'vector_lookback': vector_lb,
            'confluence_threshold': confluence_thresh,
        },
        'folds': fold_results,
        'aggregate': {
            'total_trades': total_trades,
            'total_wins': total_wins,
            'total_pnl': total_pnl,
            'profitable_folds': profitable_folds,
            'aggregate_win_rate': aggregate_wr,
            'aggregate_profit_factor': aggregate_pf,
        },
        'validated': is_validated,
    }


def print_walkforward_results(results: Dict, instrument: str):
    """Print formatted walk-forward results."""
    print("\n" + "=" * 80)
    print(f"WALK-FORWARD VALIDATION - {instrument.upper()} ({NUM_FOLDS} FOLDS)")
    print("=" * 80)
    
    # Config tested
    config = results['config']
    print(f"\n⚙️  Configuration:")
    print(f"   Vector Lookback: {config['vector_lookback']}")
    print(f"   Confluence Threshold: {config['confluence_threshold']}")
    
    # Fold-by-fold breakdown
    print(f"\n📊 FOLD-BY-FOLD RESULTS:")
    print(f"{'Fold':<6} {'Date Range':<24} {'Trades':<8} {'Win Rate':<10} {'P&L':<12} {'PF':<8} {'Status':<10}")
    print("-" * 80)
    
    for fold in results['folds']:
        if 'error' in fold and fold['error']:
            print(f"{fold['fold']:<6} {'N/A':<24} {'-':<8} {'-':<10} {'-':<12} {'-':<8} {'ERROR':<10}")
        else:
            date_range = f"{fold['start_date'][:10]} → {fold['end_date'][:10]}"
            pnl_str = f"${fold['total_pnl']:.2f}"
            pf_str = f"{fold['profit_factor']:.2f}" if fold['profit_factor'] != float('inf') else '∞'
            status = '✅ PROFIT' if fold['total_pnl'] > 0 else '❌ LOSS'
            print(f"{fold['fold']:<6} {date_range:<24} {fold['trades']:<8} {fold['win_rate']:<10.1f}% "
                  f"{pnl_str:<12} {pf_str:<8} {status:<10}")
    
    # Aggregate metrics
    agg = results['aggregate']
    print(f"\n📈 AGGREGATE METRICS:")
    print(f"   Total Trades: {agg['total_trades']}")
    print(f"   Total Wins: {agg['total_wins']}")
    print(f"   Total P&L: ${agg['total_pnl']:,.2f}")
    print(f"   Profitable Folds: {agg['profitable_folds']}/{NUM_FOLDS}")
    print(f"   Aggregate Win Rate: {agg['aggregate_win_rate']:.2f}%")
    print(f"   Aggregate Profit Factor: {agg['aggregate_profit_factor']:.2f}")
    
    # Validation status
    status = '✅ VALIDATED' if results['validated'] else '❌ NOT VALIDATED'
    print(f"\n🎯 VALIDATION STATUS: {status}")
    
    if results['validated']:
        print(f"   ✅ 5/5 folds profitable")
        print(f"   ✅ Aggregate WR ≥ 90% ({agg['aggregate_win_rate']:.1f}%)")
        print(f"   ✅ Aggregate PF ≥ 2.0 ({agg['aggregate_profit_factor']:.2f})")
    else:
        if agg['profitable_folds'] < NUM_FOLDS:
            print(f"   ❌ Only {agg['profitable_folds']}/{NUM_FOLDS} folds profitable")
        if agg['aggregate_win_rate'] < 90:
            print(f"   ❌ Aggregate WR < 90% ({agg['aggregate_win_rate']:.1f}%)")
        if agg['aggregate_profit_factor'] < 2.0:
            print(f"   ❌ Aggregate PF < 2.0 ({agg['aggregate_profit_factor']:.2f})")


if __name__ == '__main__':
    print("=" * 80)
    print("PAL VECTOR + LOG-FIB HYBRID - WALK-FORWARD VALIDATION")
    print("=" * 80)
    
    # Test configurations
    configs_to_test = list(product(VECTOR_LOOKBACKS, CONFLUENCE_THRESHOLDS))
    print(f"\n🔍 Testing {len(configs_to_test)} configurations across {NUM_FOLDS} folds...")
    print(f"   Vector Lookbacks: {VECTOR_LOOKBACKS}")
    print(f"   Confluence Thresholds: {CONFLUENCE_THRESHOLDS}")
    
    all_results = {'silver': [], 'gold': []}
    validated_configs = {'silver': [], 'gold': []}
    
    for instrument, csv_path in [('silver', SILVER_DATA), ('gold', GOLD_DATA)]:
        print(f"\n{'=' * 80}")
        print(f"INSTRUMENT: {instrument.upper()}")
        print(f"{'=' * 80}")
        
        try:
            data = load_data(csv_path)
            print(f"✅ Loaded {len(data):,} bars ({(data['datetime'].iloc[-1] - data['datetime'].iloc[0]).days} days)")
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            continue
        
        # Test each configuration
        for vector_lb, confluence_thresh in configs_to_test:
            print(f"\n  Testing LB={vector_lb}, Conf={confluence_thresh}...")
            
            results = run_walkforward(data, instrument, vector_lb, confluence_thresh)
            all_results[instrument].append(results)
            
            if results['validated']:
                validated_configs[instrument].append(results)
                print(f"    ✅ VALIDATED!")
            else:
                agg = results['aggregate']
                print(f"    ❌ Not validated (Folds: {agg['profitable_folds']}/{NUM_FOLDS}, "
                      f"WR: {agg['aggregate_win_rate']:.1f}%, PF: {agg['aggregate_profit_factor']:.2f})")
    
    # Print detailed results for validated configs
    print("\n" + "=" * 80)
    print("DETAILED RESULTS - VALIDATED CONFIGS")
    print("=" * 80)
    
    for instrument in ['silver', 'gold']:
        if validated_configs[instrument]:
            print(f"\n🏆 {instrument.upper()} - {len(validated_configs[instrument])} VALIDATED CONFIG(S):")
            for results in validated_configs[instrument]:
                print_walkforward_results(results, instrument)
        else:
            print(f"\n⚠️  {instrument.upper()}: No validated configs found")
    
    # Summary table
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    print(f"\n{'Instrument':<12} {'Configs Tested':<16} {'Validated':<12} {'Best Config':<30}")
    print("-" * 80)
    
    for instrument in ['silver', 'gold']:
        tested = len(all_results[instrument])
        validated = len(validated_configs[instrument])
        
        if validated > 0:
            # Find best by aggregate P&L
            best = max(validated_configs[instrument], key=lambda x: x['aggregate']['total_pnl'])
            best_str = f"LB={best['config']['vector_lookback']}, Conf={best['config']['confluence_threshold']}"
        else:
            best_str = "None"
        
        print(f"{instrument.upper():<12} {tested:<16} {validated:<12} {best_str:<30}")
    
    # Save results
    output_file = '/home/palbot/Projects/log-fib-scalper/walkforward_results.json'
    with open(output_file, 'w') as f:
        json.dump({
            'date': datetime.now().isoformat(),
            'num_folds': NUM_FOLDS,
            'configs_tested': len(configs_to_test),
            'silver': {
                'all_results': all_results['silver'],
                'validated_configs': validated_configs['silver'],
            },
            'gold': {
                'all_results': all_results['gold'],
                'validated_configs': validated_configs['gold'],
            },
        }, f, indent=2, default=str)
    
    print(f"\n💾 Saved: {output_file}")
    print("\n" + "=" * 80)
