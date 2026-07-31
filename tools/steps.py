import sys
sys.path.insert(0, '.')
from pathlib import Path
from lib.ingest.agent_tools import read_topic_config
import json

print("=== Step 1: read_topic_config(typography) ===")
tc = read_topic_config('typography')
print(json.dumps(tc, indent=2, ensure_ascii=False))
print()

preflight_cats = tc.get('preflight', {}).get('categories', []) or []
print(f"Preflight categories: {preflight_cats}")

if preflight_cats and 'typography' in [c.get('id') for c in preflight_cats]:
    from lib.ingest.agent_tools import read_preflight_category
    from tools.baseline import default_config
    cfg = default_config()
    prefix = '20260731120000'
    print(f"\n=== Step 2: read_preflight_category(typography) ===")
    pc = read_preflight_category(cfg, prefix, 'typography', topic='typography', max_bullets=12)
    print(json.dumps(pc, indent=2, ensure_ascii=False))
