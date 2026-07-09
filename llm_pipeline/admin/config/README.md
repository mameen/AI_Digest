# Lifecycle config (templates + manifest)

Used by **`python admin/manage.py`** — see [`../README.md`](../README.md).

| File | Purpose |
|---|---|
| `manifest.yaml` | What each nuke tier deletes / restores |
| `templates/config.yaml` | Golden pipeline config for `nuke config` |
| `templates/editorial_brief.md` | Golden brief for `nuke config` |

Refresh templates after intentional default changes on `main`:

```bash
cp config.yaml admin/config/templates/config.yaml
cp llm_pipeline/editorial_brief.md admin/config/templates/editorial_brief.md
```
