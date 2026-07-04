# CLAUDE.md

Purpose: single entrypoint for AI agents working in this repository.

## 1. Source of Truth

Read these files first, in order:

1. PROJECT_MASTER_BRIEF.md
2. docs/planning/PREBUILD_SPEC_V1.md
3. docs/planning/SPRINT_PLAN_W1_W2.md
4. docs/planning/SPRINT1_TASK_BOARD.md
5. docs/planning/SPRINT2_TASK_BOARD.md
6. docs/planning/IMPLEMENTATION_KICKOFF_CHECKLIST.md
7. docs/planning/SPRINT1_SCAFFOLDING_PLAN.md
8. docs/planning/CURRENT_STATE.md
9. docs/planning/AGENT_START_TEMPLATE.md

Canonical research/analysis sources:

- docs/agent-answers/incoming/\*.md

Rule:

- Do not modify files in docs/agent-answers/incoming unless explicitly asked.
- Normalize/decide in PROJECT_MASTER_BRIEF.md and docs/planning/\*.

## 2. Product Mode (v1)

- security-first
- privacy-first
- local-first
- read-first

Out of scope for v1 baseline:

- full write-back across all sources
- gray integrations / web scraping
- plugin marketplace

## 3. Integration Priority

Wave 1 Core:

- GitHub
- GitLab
- Jira
- Linear
- Telegram

Wave 1 Optional:

- Slack (own workspace)
- Google Calendar/Meet

Wave 2:

- Discord
- Zoom
- Teams

Wave 3:

- Rocket.Chat
- WhatsApp Business
- Viber

## 4. Security Gate (must not regress)

- JWT hardening
- tenant isolation (tenant_id + RLS)
- encryption at rest
- secrets via Vault
- CSP/HSTS
- MFA for admin paths
- append-only audit logs
- rate limits on auth/ingestion

## 5. Architecture Baseline

- Unified Event Schema is a hard contract.
- Connector Layer -> Normalization -> Storage -> Inbox read path.
- Event bus start path: Redis Streams.
- Kafka is scale-out path only.
- WASM plugin direction allowed but not a Sprint 1 blocker.

### Extensible Connector Architecture (decided 2026-06-30)

The connector system is designed to support any source, not only pre-built integrations:

- **Connector Registry**: the `connectors` DB table tracks all registered connectors (built-in and custom). Every connector has a `source_type`, `tenant_id`, `status`, and optional auth config.
- **Generic HTTP Connector**: a configurable connector that can poll any REST API endpoint. The user specifies: URL, auth method (API key / Bearer / Basic), polling interval, and a field mapping to UnifiedEvent fields (`externalId`, `timestamp`, `preview`). No code change required to add a new source.
- **Webhook Receiver**: `POST /webhooks/{connector_id}` — any external service can push events to ALLinO. The connector_id maps to a registered connector entry. Supports HMAC signature verification per connector config.
- **Pre-built connectors** (GitHub, GitLab, Linear, etc.) are implemented as named profiles on top of the same BaseConnector contract — they are not special-cased at the architecture level.

This means: adding a new source = registering a connector entry (via UI or API), not writing Python code. Custom / internal tools are first-class citizens.

## 6. UX/UI Baseline

- Core shell: Inbox, Focus, Incident, Security Center, Settings.
- Thread View as overlay/panel.
- Error and empty states are mandatory for MVP usability.
- Current visual baseline: docs/agent-answers/incoming/secureinbox-design-spec.md (variant 1).
- Future design variants should be compared, not auto-replaced.

### Design Handoff (added 2026-06-30)

High-fidelity design is in `docs/design_handoff_secure_inbox/`:

- `secure-inbox-spec.html` — open in browser; live concept + 6 spec sections (tokens, components, states, responsive, a11y, React+Tailwind snippets). Use the switcher to preview 3 directions × light/dark.
- `tokens.css` — all design tokens as CSS custom properties.
- `README.md` — full component spec (InboxItem, SecurityCard, SourceBadge, PriorityBadge, CommandPalette, ThreadPanel).

**Chosen direction: Quiet Slate / light** (default, WCAG AA). Token names are direction-stable — code against CSS vars, never hardcode hex values.

**Rules for all UI work:**

1. Always code against CSS custom properties from `globals.css` (e.g. `var(--accent)`, `var(--surface-2)`, `var(--r-card)`). Never hardcode colors, radii, or shadows.
2. Theme is controlled by `data-direction` + `data-theme` on `<html>`. Do not add inline styles that override the token system.
3. When implementing a component, read the corresponding spec section in `README.md` and the React+Tailwind snippets in `secure-inbox-spec.html` first.
4. Three-pane layout (nav rail 218px · message list 382px · thread panel flex). Match the spec dimensions at ≥1100px; tablet/mobile breakpoints are in `README.md`.
5. Accessibility is mandatory: 2px focus rings via `--accent-ring`, no color-only cues, `aria-label` on inbox rows, `role="list"` on the list, `prefers-reduced-motion` respected via `globals.css`.
6. Typography: Public Sans for UI/headings, IBM Plex Mono for meta/shortcuts. Both are loaded via Google Fonts in `layout.tsx`.

## 7. Working Conventions for Agents

- Keep changes minimal and scoped.
- Prefer incremental delivery and keep task boards updated.
- If a decision changes scope/security, add a short dated note in planning docs.
- Do not introduce dependencies or integrations not required by current sprint goals.

## 8. Startup Checklist for Any New Agent Session

1. Read this file.
2. Read PROJECT_MASTER_BRIEF.md section 1.2/1.3/1.4.
3. Open current sprint board and move one task to in-progress.
4. Implement only what is needed for sprint exit criteria.
