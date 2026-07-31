# Hermes Archive Notes

This folder keeps the stable Hermes architecture docs. Temporary track handoff
files were removed during archive cleanup because they described active Agent
2/Agent 3 coordination rather than the finished POC.

## Preserved Conclusions

1. The staged `llm_pipeline/` POC remains the stable baseline.
2. The Hermes POC is valuable as a multi-agent reference implementation, not as
   the leanest runtime for this bounded daily digest workload.
3. The single-agent-with-skills direction is the preferred future shape because
   it can keep deterministic Python boundaries while reducing handoff overhead.
4. Approved public report and diagnostics artifacts live in `app/`.

## Keep

| Doc | Why |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Stable architecture description |
| [`../POC.md`](../POC.md) | Runbook and local validation notes |
| [`../working_agreements.md`](../working_agreements.md) | Role artifact contracts |
| [`../system_roles.md`](../system_roles.md) | Role responsibilities |

## Removed as Handoff Noise

The deleted track files captured temporary branch coordination, import maps, and
coverage snapshots. Their useful architectural takeaway is summarized above.
