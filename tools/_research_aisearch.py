#!/usr/bin/env python3
"""Quick research script for aisearch topic — kanban task t_1d29e883."""

import sys, json
sys.path.insert(0, '/c/dev/personal/.repos/AI_Digest')
from lib.ingest.agent_tools import read_topic_config
print(json.dumps(read_topic_config('aisearch'), indent=2))
