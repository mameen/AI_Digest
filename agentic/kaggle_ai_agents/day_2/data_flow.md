# Data Flow

```mermaid
flowchart LR
	C[config/project.yaml] --> F[fetch tools]
	F --> N[normalize]
	N --> DS[dedupe and score]
	DS --> S[selected items]
	S --> V[schema validation]
	V --> M[markdown output]
	V --> J[json output]
	V --> X[diagnostics]
```

1. config/project.yaml defines sources.
2. tools fetch and normalize items.
3. normalized items enter dedupe and scoring.
4. selected items pass schema validation.
5. renderer writes markdown and json outputs.
