#!/bin/bash
# CFD Scalping Scanner - Gold & Silver
# Runs every 5 minutes, outputs alerts to stdout

cd /home/palbot/Projects/log-fib-scalper
source .venv/bin/activate

python scanner/scalping_scanner.py --scan 2>&1
