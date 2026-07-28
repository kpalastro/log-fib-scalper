import json
from datetime import datetime

with open('scanner/alert_history.json') as f:
    data = json.load(f)

today = [a for a in data if '2026-05-20' in a['timestamp']]
print(f"Alerts today (2026-05-20): {len(today)}")
for a in today[-10:]:
    print(f"  {a['instrument'].upper()} | {a['direction']:5} | Score: {a['score']:5.1f} | Price: ${a['price']:.2f} | Entry: ${a['entry']:.2f} | TP: ${a['tp']:.2f} | SL: ${a['sl']:.2f}")
