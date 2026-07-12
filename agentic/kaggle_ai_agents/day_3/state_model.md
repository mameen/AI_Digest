# State Model

```mermaid
stateDiagram-v2
	[*] --> ingest
	ingest --> dedupe
	dedupe --> rank
	rank --> render
	render --> done
	ingest --> failed
	dedupe --> failed
	rank --> failed
	render --> failed
```

## Run State

- run_id
- started_at
- phase: ingest | dedupe | rank | render | done | failed
- source_status map
- errors list

## Task State

- task_id
- input_digest
- attempts
- result_status
