"""
Pal Vector Hybrid - 60-Day Extended Backtest
=============================================

Run comprehensive backtest on full 60-day dataset.
Generates detailed performance metrics and trade analysis.

Usage:
    python pal_vector_60day.py [--instrument silver|gold]
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict
from strategies.pal_vector_hybrid import VectorLogFibHybrid, load_data

# Data paths
SILVER_DATA = '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv'
GOLD_DATA = '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv'


class ExtendedBacktester:
    """Extended backtester with detailed analytics."""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
    
    def run(self, data: pd.DataFrame, instrument: str, 
            vector_lb: int, confluence_thresh: int) -> Dict:
        """
        Run extended backtest with full analytics.
        
        Returns:
            Dict with performance metrics, equity curve, trade stats
        """
        strategy = VectorLogFibHybrid(instrument=instrument)
        strategy.vector_lb = vector_lb
        
        trades = []
        capital = self.initial_capital
        position = None
        equity_curve = []
        daily_pnl = {}
        
        warmup = max(strategy.vector_lb, strategy.logfib_config['lookback']) + 10
        
        for i in range(warmup, len(data)):
            analysis = strategy.analyze(data, i)
            current_price = data['close'].iloc[i]
            timestamp = data['datetime'].iloc[i]
            date_str = timestamp.strftime('%Y-%m-%d')
            
            # Track equity
            equity_curve.append({
                'timestamp': timestamp,
                'capital': capital,
                'price': current_price,
            })
            
            # Entry
            if position is None and analysis['signal'] == 'ENTER' and analysis['confluence'] >= confluence_thresh:
                logfib = analysis['logfib']
                size = capital * 0.1 / current_price  # 10% position
                
                position = {
                    'direction': analysis['direction'],
                    'entry_price': logfib['entry'],
                    'size': size,
                    'tp': logfib['tp'],
                    'sl': logfib['sl'],
                    'entry_time': timestamp,
                    'entry_bar': i,
                    'confluence': analysis['confluence'],
                }
            
            # Exit
            elif position is not None:
                pnl = 0
                exit_reason = None
                exit_price = 0
                exit_bar = i
                
                if position['direction'] == 'LONG':
                    if data['high'].iloc[i] >= position['tp']:
                        exit_price = position['tp']
                        pnl = (exit_price - position['entry_price']) * position['size']
                        exit_reason = 'TP'
                    elif data['low'].iloc[i] <= position['sl']:
                        exit_price = position['sl']
                        pnl = (exit_price - position['entry_price']) * position['size']
                        exit_reason = 'SL'
                else:  # SHORT
                    if data['low'].iloc[i] <= position['tp']:
                        exit_price = position['tp']
                        pnl = (position['entry_price'] - exit_price) * position['size']
                        exit_reason = 'TP'
                    elif data['high'].iloc[i] >= position['sl']:
                        exit_price = position['sl']
                        pnl = (position['entry_price'] - exit_price) * position['size']
                        exit_reason = 'SL'
                
                if exit_reason:
                    bars_held = exit_bar - position['entry_bar']
                    trade = {
                        'entry_time': position['entry_time'],
                        'exit_time': timestamp,
                        'direction': position['direction'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': exit_reason,
                        'confluence': position['confluence'],
                        'bars_held': bars_held,
                        'duration_hours': bars_held * 5 / 60,  # 5-min bars
                    }
                    trades.append(trade)
                    capital += pnl
                    
                    # Track daily P&L
                    if date_str not in daily_pnl:
                        daily_pnl[date_str] = 0
                    daily_pnl[date_str] += pnl
                    
                    position = None
        
        if not trades:
            return {'error': 'No trades executed'}
        
        # Calculate comprehensive metrics
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] <= 0]
        
        total_pnl = sum(t['pnl'] for t in trades)
        gross_profit = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in losses))
        
        # Win/loss stats
        avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0
        largest_win = max([t['pnl'] for t in wins]) if wins else 0
        largest_loss = min([t['pnl'] for t in losses]) if losses else 0
        
        # Consecutive wins/losses
        max_consec_wins = self._max_consecutive(wins, losses, 'win')
        max_consec_losses = self._max_consecutive(wins, losses, 'loss')
        
        # Drawdown calculation
        peak = self.initial_capital
        max_drawdown = 0
        for eq in equity_curve:
            if eq['capital'] > peak:
                peak = eq['capital']
            drawdown = (peak - eq['capital']) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Sharpe ratio (annualized, assuming 252 trading days)
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i]['capital'] - equity_curve[i-1]['capital']) / equity_curve[i-1]['capital']
            returns.append(ret)
        
        if len(returns) > 1:
            daily_returns = np.array(returns)
            sharpe = np.sqrt(252) * np.mean(daily_returns) / np.std(daily_returns) if np.std(daily_returns) > 0 else 0
        else:
            sharpe = 0
        
        # Profit factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Recovery factor
        recovery_factor = total_pnl / max_drawdown if max_drawdown > 0 else float('inf')
        
        # Expected value per trade
        expected_value = total_pnl / len(trades)
        
        return {
            'instrument': instrument,
            'config': {
                'vector_lookback': vector_lb,
                'confluence_threshold': confluence_thresh,
                'logfib_config': strategy.logfib_config,
            },
            'data_range': {
                'start': str(data['datetime'].iloc[0]),
                'end': str(data['datetime'].iloc[-1]),
                'total_bars': len(data),
                'days': (data['datetime'].iloc[-1] - data['datetime'].iloc[0]).days,
            },
            'performance': {
                'total_trades': len(trades),
                'wins': len(wins),
                'losses': len(losses),
                'win_rate': len(wins) / len(trades) * 100,
                'total_pnl': total_pnl,
                'final_capital': capital,
                'return_pct': (capital - self.initial_capital) / self.initial_capital * 100,
                'profit_factor': profit_factor,
                'recovery_factor': recovery_factor,
                'sharpe_ratio': sharpe,
                'max_drawdown': max_drawdown,
                'expected_value': expected_value,
            },
            'trade_stats': {
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'largest_win': largest_win,
                'largest_loss': largest_loss,
                'avg_bars_held': np.mean([t['bars_held'] for t in trades]),
                'avg_duration_hours': np.mean([t['duration_hours'] for t in trades]),
                'max_consec_wins': max_consec_wins,
                'max_consec_losses': max_consec_losses,
            },
            'confluence_stats': {
                'avg_confluence': np.mean([t['confluence'] for t in trades]),
                'avg_confluence_wins': np.mean([t['confluence'] for t in wins]) if wins else 0,
                'avg_confluence_losses': np.mean([t['confluence'] for t in losses]) if losses else 0,
            },
            'daily_pnl': daily_pnl,
            'trades': trades,
            'equity_curve': equity_curve,
        }
    
    def _max_consecutive(self, wins, losses, win_or_loss: str) -> int:
        """Calculate max consecutive wins or losses."""
        trades = sorted(wins + losses, key=lambda x: x['entry_time'])
        max_consec = 0
        current_consec = 0
        
        for t in trades:
            is_win = t['pnl'] > 0
            if (win_or_loss == 'win' and is_win) or (win_or_loss == 'loss' and not is_win):
                current_consec += 1
                max_consec = max(max_consec, current_consec)
            else:
                current_consec = 0
        
        return max_consec


def print_results(results: Dict):
    """Print formatted results."""
    print("\n" + "=" * 80)
    print(f"60-DAY BACKTEST RESULTS - {results['instrument'].upper()}")
    print("=" * 80)
    
    print(f"\n📅 Data Range: {results['data_range']['start'][:10]} → {results['data_range']['end'][:10]}")
    print(f"   Total Bars: {results['data_range']['total_bars']:,} | Days: {results['data_range']['days']}")
    
    print(f"\n⚙️  Configuration:")
    print(f"   Vector Lookback: {results['config']['vector_lookback']}")
    print(f"   Confluence Threshold: {results['config']['confluence_threshold']}")
    print(f"   Log-Fib: LB={results['config']['logfib_config']['lookback']}, "
          f"Mult={results['config']['logfib_config']['mult']}, "
          f"Entry={results['config']['logfib_config']['entry']}")
    
    print(f"\n📊 PERFORMANCE METRICS:")
    perf = results['performance']
    print(f"   Total Trades: {perf['total_trades']}")
    print(f"   Win Rate: {perf['win_rate']:.2f}%")
    print(f"   Total P&L: ${perf['total_pnl']:,.2f}")
    print(f"   Return: {perf['return_pct']:.2f}%")
    print(f"   Profit Factor: {perf['profit_factor']:.2f}")
    print(f"   Recovery Factor: {perf['recovery_factor']:.2f}")
    print(f"   Sharpe Ratio: {perf['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown: {perf['max_drawdown']:.2f}%")
    print(f"   Expected Value: ${perf['expected_value']:.2f}/trade")
    
    print(f"\n📈 TRADE STATISTICS:")
    stats = results['trade_stats']
    print(f"   Avg Win: ${stats['avg_win']:.2f}")
    print(f"   Avg Loss: ${stats['avg_loss']:.2f}")
    print(f"   Largest Win: ${stats['largest_win']:.2f}")
    print(f"   Largest Loss: ${stats['largest_loss']:.2f}")
    print(f"   Avg Bars Held: {stats['avg_bars_held']:.1f} ({stats['avg_duration_hours']:.1f} hours)")
    print(f"   Max Consecutive Wins: {stats['max_consec_wins']}")
    print(f"   Max Consecutive Losses: {stats['max_consec_losses']}")
    
    print(f"\n🎯 CONFLUENCE ANALYSIS:")
    conf = results['confluence_stats']
    print(f"   Avg Confluence (All): {conf['avg_confluence']:.1f}")
    print(f"   Avg Confluence (Wins): {conf['avg_confluence_wins']:.1f}")
    print(f"   Avg Confluence (Losses): {conf['avg_confluence_losses']:.1f}")
    
    # Trade log (first 10)
    print(f"\n📝 TRADE LOG (First 10):")
    print(f"{'#':<3} {'Date':<12} {'Dir':<5} {'Entry':<10} {'Exit':<10} {'P&L':<10} {'Conf':<5} {'Reason':<6}")
    print("-" * 80)
    for i, t in enumerate(results['trades'][:10], 1):
        date = t['entry_time'].strftime('%Y-%m-%d')
        pnl_str = f"${t['pnl']:.2f}" if t['pnl'] >= 0 else f"-${abs(t['pnl']):.2f}"
        color = '+' if t['pnl'] > 0 else ''
        print(f"{i:<3} {date:<12} {t['direction']:<5} {t['entry_price']:<10.4f} {t['exit_price']:<10.4f} {pnl_str:<10} {t['confluence']:<5.0f} {t['exit_reason']:<6}")
    
    if len(results['trades']) > 10:
        print(f"... and {len(results['trades']) - 10} more trades")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='60-Day Extended Backtest')
    parser.add_argument('--instrument', type=str, default='both', choices=['silver', 'gold', 'both'])
    parser.add_argument('--vector-lb', type=int, default=None, help='Vector lookback (default: optimal per instrument)')
    parser.add_argument('--confluence', type=int, default=50, help='Confluence threshold (default: 50)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("PAL VECTOR + LOG-FIB HYBRID - 60-DAY EXTENDED BACKTEST")
    print("=" * 80)
    
    instruments = []
    if args.instrument == 'both':
        instruments = [('silver', SILVER_DATA), ('gold', GOLD_DATA)]
    elif args.instrument == 'silver':
        instruments = [('silver', SILVER_DATA)]
    else:
        instruments = [('gold', GOLD_DATA)]
    
    all_results = {}
    
    for instrument, csv_path in instruments:
        print(f"\n{'=' * 80}")
        print(f"PROCESSING: {instrument.upper()}")
        print(f"{'=' * 80}")
        
        try:
            data = load_data(csv_path)
            print(f"✅ Loaded {len(data):,} bars")
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            continue
        
        # Use optimal configs from sweep
        if args.vector_lb:
            vector_lb = args.vector_lb
        else:
            vector_lb = 20 if instrument == 'silver' else 30
        
        backtester = ExtendedBacktester(initial_capital=100000)
        results = backtester.run(data, instrument, vector_lb, args.confluence)
        
        if 'error' not in results:
            print_results(results)
            
            # Save results
            output_file = f'/home/palbot/Projects/log-fib-scalper/extended_backtest_{instrument}_60day.json'
            with open(output_file, 'w') as f:
                # Remove equity_curve for compact JSON
                results_save = {k: v for k, v in results.items() if k != 'equity_curve'}
                json.dump(results_save, f, indent=2, default=str)
            print(f"\n💾 Saved: {output_file}")
            
            all_results[instrument] = results
        else:
            print(f"\n❌ {results['error']}")
    
    # Summary
    if all_results:
        print("\n" + "=" * 80)
        print("60-DAY SUMMARY")
        print("=" * 80)
        print(f"{'Instrument':<12} {'Trades':<8} {'Win Rate':<10} {'P&L':<12} {'Return':<10} {'PF':<8} {'Sharpe':<8}")
        print("-" * 80)
        for inst, res in all_results.items():
            perf = res['performance']
            print(f"{inst.upper():<12} {perf['total_trades']:<8} {perf['win_rate']:<10.2f}% "
                  f"${perf['total_pnl']:<11,.2f} {perf['return_pct']:<10.2f}% "
                  f"{perf['profit_factor']:<8.2f} {perf['sharpe_ratio']:<8.2f}")
    
    print("\n" + "=" * 80)
