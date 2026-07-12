# Architecture Draft

```mermaid
flowchart LR
	S[Sources] --> I[Ingest]
	I --> N[Normalize]
	N --> D[Dedupe and Score]
	D --> T[Top-K Selection]
	T --> V[Schema Validation]
	V --> R[Render Markdown and JSON]
```

## Flow

1. Ingest source items
2. Normalize fields (title, url, summary, source)
3. Score and deduplicate
4. Select top cards
5. Validate output schema
6. Render markdown and json

## Components

- tools: source adapters
- workflow: orchestration logic
- validation: schema checks
- rendering: user-facing output

```mermaid
flowchart TB
	subgraph Agent System
		W[workflow]
		T[tools]
		V[validation]
		R[rendering]
	end

	CFG[config/project.yaml] --> W
	W --> T
	T --> W
	W --> V
	V --> R
	R --> OUT[brief artifacts]
```
