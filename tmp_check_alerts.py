import json

with open('scanner/alert_history.json') as f:
    alerts = json.load(f)

# Get most recent gold and silver alerts
gold_alerts = [a for a in alerts if a['instrument'] == 'gold']
silver_alerts = [a for a in alerts if a['instrument'] == 'silver']

print('=== MOST RECENT ACTIVE SETUPS ===')
if gold_alerts:
    g = gold_alerts[-1]
    print(f"GOLD {g['direction']} @ {g['price']:.2f}")
    print(f"  Score: {g['score']:.1f}")
    print(f"  Entry: {g['entry']:.2f}, TP: {g['tp']:.2f}, SL: {g['sl']:.2f}")
    print(f"  Time: {g['datetime']}")
    
if silver_alerts:
    s = silver_alerts[-1]
    print(f"SILVER {s['direction']} @ {s['price']:.2f}")
    print(f"  Score: {s['score']:.1f}")
    print(f"  Entry: {s['entry']:.2f}, TP: {s['tp']:.2f}, SL: {s['sl']:.2f}")
    print(f"  Time: {s['datetime']}")
