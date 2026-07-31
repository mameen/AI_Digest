import sys, json
sys.path.insert(0, r'/c/dev/personal/.repos/AI_Digest')
from lib.ingest.agent_tools import read_topic_config
result = read_topic_config('agentic-ai')
print(json.dumps(result, indent=2, default=str))
