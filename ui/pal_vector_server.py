"""
Pal Vector Visualizer - Flask API Server
=========================================

Serves the visualizer HTML and provides analysis API endpoints.

Usage:
    python pal_vector_server.py [--port 8080] [--instrument silver|gold]

Access:
    http://localhost:8080
"""

import sys
import os
from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import pandas as pd
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.pal_vector_scalper import (
    PalVectorCalculator,
    VectorLogFibConfluence,
    VectorBacktester,
    load_data
)

app = Flask(__name__)
CORS(app)

# Data paths
SILVER_DATA = '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv'
GOLD_DATA = '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv'
VISUALIZER_HTML = '/home/palbot/Projects/log-fib-scalper/ui/pal_vector_visualizer.html'


@app.route('/')
def index():
    """Serve the visualizer HTML."""
    return send_file(VISUALIZER_HTML)


@app.route('/api/analyze')
def analyze():
    """
    Analyze current market state with Vector + Log-Fib confluence.
    
    Query params:
        instrument: silver|gold (default: silver)
        vector_lb: Vector lookback (default: 100)
        logfib_lb: Log-Fib lookback (default: 6)
    """
    instrument = request.args.get('instrument', 'silver').lower()
    vector_lb = int(request.args.get('vector_lb', 100))
    logfib_lb = int(request.args.get('logfib_lb', 6))
    
    csv_path = GOLD_DATA if instrument == 'gold' else SILVER_DATA
    
    try:
        data = load_data(csv_path)
    except Exception as e:
        return jsonify({'error': str(e)})
    
    # Run analysis
    confluence_engine = VectorLogFibConfluence(
        vector_lookback=vector_lb,
        logfib_config={
            'lookback': logfib_lb,
            'mult': 0.5 if instrument == 'silver' else 0.618,
            'entry': 0.382,
            'tp': 1.272,
            'sl': 1.618,
        }
    )
    
    analysis = confluence_engine.analyze(data)
    
    # Get vector calculator for levels
    vector_calc = PalVectorCalculator(lookback=vector_lb)
    current_vectors = vector_calc.get_current_vector_levels(data)
    
    # Format candles for chart (last 200 bars)
    recent_data = data.tail(200)
    candles = []
    for _, row in recent_data.iterrows():
        candles.append({
            'datetime': str(row['datetime']),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': float(row.get('volume', 0)),
        })
    
    # Run quick backtest
    backtester = VectorBacktester(initial_capital=100000)
    backtest_results = backtester.run(data)
    
    # Format backtest trades
    if 'trades' in backtest_results:
        backtest_results['trades'] = backtest_results['trades'][-50:]  # Last 50 trades
    
    return jsonify({
        'instrument': instrument,
        'candles': candles,
        'analysis': {
            'current_price': float(analysis.get('vector_analysis', {}).get('current_price', 0)),
            'vector_analysis': {
                'trend': current_vectors.get('trend', 'NEUTRAL'),
                'swing_high': float(current_vectors.get('swing_high', 0)),
                'swing_low': float(current_vectors.get('swing_low', 0)),
                'hb': current_vectors.get('hb', 0),
                'lb': current_vectors.get('lb', 0),
                'high_projections': {k: float(v) for k, v in current_vectors.get('high_projections', {}).items()},
                'low_projections': {k: float(v) for k, v in current_vectors.get('low_projections', {}).items()},
            },
            'logfib_analysis': {
                k: (float(v) if isinstance(v, (int, float)) else v)
                for k, v in analysis.get('logfib_analysis', {}).items()
            },
            'confluence_score': float(analysis.get('confluence_score', 0)),
            'signal': analysis.get('signal', {}),
        },
        'vector_levels': current_vectors,
        'backtest': backtest_results,
    })


@app.route('/api/backtest')
def backtest():
    """
    Run full backtest with custom parameters.
    
    Query params:
        instrument: silver|gold
        lookback: Vector lookback (default: 100)
        lb_lookback: Log-Fib lookback (default: 6)
        mult: Log-Fib multiplier
        entry: Entry ratio
        tp: Take profit ratio
        sl: Stop loss ratio
    """
    instrument = request.args.get('instrument', 'silver').lower()
    csv_path = GOLD_DATA if instrument == 'gold' else SILVER_DATA
    
    config = {
        'lookback': int(request.args.get('lookback', 100)),
        'mult': float(request.args.get('mult', 0.5 if instrument == 'silver' else 0.618)),
        'entry': float(request.args.get('entry', 0.382)),
        'tp': float(request.args.get('tp', 1.272)),
        'sl': float(request.args.get('sl', 1.618)),
    }
    
    try:
        data = load_data(csv_path)
    except Exception as e:
        return jsonify({'error': str(e)})
    
    backtester = VectorBacktester(initial_capital=100000)
    results = backtester.run(data, config)
    
    return jsonify(results)


@app.route('/api/instruments')
def instruments():
    """List available instruments and data status."""
    instruments = {}
    
    for name, path in [('silver', SILVER_DATA), ('gold', GOLD_DATA)]:
        if os.path.exists(path):
            try:
                data = load_data(path)
                instruments[name] = {
                    'available': True,
                    'bars': len(data),
                    'last_update': str(data['datetime'].iloc[-1]),
                    'price': float(data['close'].iloc[-1]),
                }
            except Exception as e:
                instruments[name] = {
                    'available': False,
                    'error': str(e),
                }
        else:
            instruments[name] = {
                'available': False,
                'error': 'Data file not found',
            }
    
    return jsonify(instruments)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Pal Vector Visualizer Server')
    parser.add_argument('--port', type=int, default=8080, help='Port to run server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    print(f"🚀 Starting Pal Vector Visualizer Server")
    print(f"📊 Access at: http://localhost:{args.port}")
    print(f"📁 Silver data: {SILVER_DATA}")
    print(f"📁 Gold data: {GOLD_DATA}")
    print(f"📄 Visualizer: {VISUALIZER_HTML}")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host=args.host, port=args.port, debug=args.debug)
