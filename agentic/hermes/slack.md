# Slack + Hermes — setup steps

> **Canonical narrative:** [`README.md`](../../README.md) at the repo root. Concierge
> is the Slack front desk for AI Digest GO and status — not story fetching.
> **If this doc conflicts with README, README wins.**

> **Scratch notes:** [`slack_deleteme.md`](slack_deleteme.md) (gitignored — **only** place for secrets while experimenting; never commit).
>
> **Canonical upstream doc:** [Hermes — Slack (Socket Mode)](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack)

Hermes connects via **Socket Mode** (WebSocket) — no public URL, works on your laptop behind a firewall.

Configure in **Hermes dashboard** (Messaging → Slack) *or* `~/.hermes/.env` — same values.

---

## Your app

| Field | Value |
|---|---|
| Name | ADemiry Demo App |
| App ID | `A093YSL7BHD` |
| Console | https://api.slack.com/apps/A093YSL7BHD |
| Distribution | Not distributed (single workspace) |

---

## Hermes UI ↔ tokens (cheat sheet)

| Hermes dashboard field | Token / value | Where to get it |
|---|---|---|
| **Slack bot token** | `xoxb-…` | Slack → **OAuth & Permissions** → Bot User OAuth Token (after Install to Workspace) |
| **Slack app token** | `xapp-…` | Slack → **Socket Mode** → App-Level Token (`connections:write`) |
| **Allowed Slack member IDs** | `U…`, `U…` | Slack → your profile → ⋮ → **Copy member ID** |
| **Allow all users?** | `false` for prod; `true` dev only | Hermes UI |
| **Home channel ID** | `C…` | Channel → right-click → View details → Channel ID at bottom |
| **Home channel display name** | e.g. `#digest-bot` | Label only (optional) |

Equivalent `.env` (profile home, e.g. `~/.hermes/.env`):

```bash
# Copy template: cp agentic/hermes/config/hermes.env.example ~/.hermes/.env
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_ALLOWED_USERS=U0123456789
SLACK_HOME_CHANNEL=C0123456789
SLACK_HOME_CHANNEL_NAME=digest-bot
```

Templates (placeholders, safe to commit):

| Template | Copy to | Purpose |
|---|---|---|
| [`config/hermes.env.example`](config/hermes.env.example) | `~/.hermes/.env` | Slack tokens, allowlist |
| [`config/hermes.config.example.yaml`](config/hermes.config.example.yaml) | merge into `~/.hermes/config.yaml` | Slack platform behaviour |
| [`config/digest.agentic.example.yaml`](config/digest.agentic.example.yaml) | merge into repo `config.yaml` | In-repo model routing (future) |

Secrets never go in the repo. Scratch notes while experimenting:
[`slack_deleteme.md`](slack_deleteme.md) (gitignored).

---

## Step-by-step

### 0. Generate manifest (recommended — easiest)

Hermes pre-builds scopes, events, slash commands, and Socket Mode:

```bash
hermes slack manifest --write
# writes ~/.hermes/slack-manifest.json
```

**Existing app (`A093YSL7BHD`):** Slack → **App Manifest** → Edit → paste JSON → Save → **reinstall** if prompted.

**New app:** https://api.slack.com/apps → Create New App → **From an app manifest** → paste → Create.

Then jump to **Step 5** (install + tokens).

Official: [Hermes Slack § Step 1 Option A](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#option-a-from-a-hermes-generated-manifest-recommended)

---

### 1. Create app (manual — if not using manifest)

https://api.slack.com/apps → Create New App → **From scratch** → name **ADemiry Demo App** → pick workspace.

---

### 2. Bot token scopes

Slack → **Features → OAuth & Permissions → Bot Token Scopes**. Add:

| Scope | Why |
|---|---|
| `chat:write` | Send messages |
| `app_mentions:read` | @mentions |
| `channels:history`, `channels:read` | Public channels |
| `groups:history` | Private channels |
| `im:history`, `im:read`, `im:write` | DMs |
| `mpim:history`, `mpim:read` | Group DMs |
| `users:read` | User lookup |
| `files:read`, `files:write` | Attachments |

---

### 3. Enable Socket Mode + app token

Slack → **Settings → Socket Mode** → **Enable** → create App-Level Token:

- Name: `hermes-socket`
- Scope: **`connections:write`**
- Copy token → starts with **`xapp-`** → paste into Hermes **Slack app token**

Must be `xapp-`, not `xoxb-`.

---

### 4. Event subscriptions

Slack → **Features → Event Subscriptions** → Enable → **Subscribe to bot events**:

| Event | Required |
|---|---|
| `message.im` | Yes — DMs |
| `message.channels` | Yes — public channels |
| `message.groups` | Yes — private channels |
| `message.mpim` | Yes — group DMs |
| `app_mention` | Yes |

Save. **Reinstall app** after any scope/event change.

---

### 5. App Home (DMs)

Slack → **Features → App Home** → **Messages Tab** ON → allow messages from tab.

Without this, DMs show *"Sending messages to this app has been turned off"*.

---

### 6. Install + bot token

Slack → **Settings → Install App** → **Install to Workspace** → Allow.

Copy **Bot User OAuth Token** (`xoxb-…`) → Hermes **Slack bot token**.

---

### 7. Your member ID (allowlist)

In Slack: your avatar → **View full profile** → ⋮ → **Copy member ID** (`U…`).

Paste into Hermes **Allowed Slack member IDs** (comma-separated for multiple users).

Without allowlist, Hermes denies messages by default ([security](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#security)).

---

### 8. Hermes dashboard + gateway

1. Open Hermes dashboard → **Messaging → Slack**
2. Paste **bot token**, **app token**, **allowed member IDs**
3. Optional: **Home channel ID** (cron/notifications), display name
4. Save
5. Start gateway:

```bash
python agentic/hermes/admin/manage.py hermes gateway start
# or: hermes gateway
python agentic/hermes/admin/manage.py hermes doctor
```

Or interactive: `hermes gateway setup` → select Slack.

---

### 9. Invite bot + smoke test

In Slack channel:

```
/invite @ADemiry Demo App
```

| Test | Expected |
|---|---|
| DM the bot | Reply (no @mention needed) |
| @mention in channel | Reply in thread |
| Unauthorized user | Ignored / pairing prompt |

---

## Troubleshooting (common)

| Symptom | Fix |
|---|---|
| UI: **Messaging gateway stopped** | `hermes gateway start` (or dashboard start) |
| DMs blocked | Enable **Messages Tab** (Step 5) |
| Works in DM, not channel | Add `message.channels` + `channels:history`; reinstall; `/invite` |
| `invalid_auth` | Regenerate tokens; `xapp-` vs `xoxb-` swapped |
| Changed scopes, no effect | **Reinstall app to workspace** |
| Dashboard vs `.env` | Same keys; profile `.env` at `~/.hermes/.env` or `~/.hermes/profiles/<name>/.env` |

Full table: [Hermes Slack troubleshooting](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#troubleshooting)

---

## Other references

| Doc | URL |
|---|---|
| **Hermes Slack (primary)** | https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack |
| Slack Socket Mode (platform) | https://docs.slack.dev/apis/events-api/using-socket-mode |
| Slack Bolt Python Socket Mode | https://slack.dev/tools/bolt-python/concepts/socket-mode |
| SFAI Labs — token types explained | https://sfailabs.com/guides/how-to-get-slack-bot-token |

---

## Related (this repo)

- [`system_roles.md`](system_roles.md) — Concierge = Slack front desk
- [`admin/README.md`](admin/README.md) — agentic Hermes admin
- [`../../../admin/README.md`](../../../admin/README.md) — pipeline admin
