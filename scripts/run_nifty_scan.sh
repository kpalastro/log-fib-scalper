#!/bin/bash
# Nifty Geometric Scanner
# Runs every 5 minutes during market hours (9-15 IST, Mon-Fri)

cd /home/palbot/Projects/log-fib-scalper
source .venv/bin/activate

python scanner/nifty_scanner.py --scan 2>&1
