import json

data = json.load(open('scanner/alert_history.json'))
gold = [a for a in data if a['instrument'] == 'gold']
silver = [a for a in data if a['instrument'] == 'silver']

print(f"GOLD alerts: {len(gold)}")
print(f"SILVER alerts: {len(silver)}")

if gold:
    g = gold[-1]
    print(f"\n=== LATEST GOLD ALERT ===")
    print(f"Time: {g['datetime']}")
    print(f"Direction: {g['direction']}")
    print(f"Score: {g['score']:.1f}")
    print(f"Entry: ${g['entry']:.2f}")
    print(f"TP: ${g['tp']:.2f}")
    print(f"SL: ${g['sl']:.2f}")

if silver:
    s = silver[-1]
    print(f"\n=== LATEST SILVER ALERT ===")
    print(f"Time: {s['datetime']}")
    print(f"Direction: {s['direction']}")
    print(f"Score: {s['score']:.1f}")
    print(f"Entry: ${s['entry']:.2f}")
    print(f"TP: ${s['tp']:.2f}")
    print(f"SL: ${s['sl']:.2f}")
