# Sprint 21 — Onboarding screen (connect-a-source gate, skippable)

Opened: 2026-07-03. Closed: 2026-07-03.

## Context

User delegated again ("продолжай сам" — continue on your own), with no
specific task. Ran a research agent (Explore) to cross-reference
`PROJECT_MASTER_BRIEF.md` and `docs/planning/PREBUILD_SPEC_V1.md` against
`CURRENT_STATE.md`'s changelog for any canonical requirement that's neither
implemented nor already-explicitly-deferred (WhatsApp/Viber, Postgres+RLS,
threads/users cleanup, Google push, Zoom/Teams reply, and further built-in
auto-polling are all already off the table — see the Sprint 19/20 guardrail
notes).

The agent surfaced onboarding as the strongest candidate: both
`PROJECT_MASTER_BRIEF.md:97` ("Онбординг должен требовать подключение
минимум одного источника, но не блокировать пользователя навсегда при
Skip") and `docs/planning/PREBUILD_SPEC_V1.md:68` ("Onboarding: минимум
один источник, но без жесткой блокировки пользователя навсегда") state this
as a UX/IA baseline requirement. Verified independently before starting:
grepped `frontend/src` for onboarding/welcome/wizard/get-started — zero
hits, confirming it was never built, not just undocumented. Matches the
exact "pure frontend, reuses already-tested backend, no new infra or
security surface" shape already proven low-risk in Sprints 13/16/20.

The agent's other two candidates were explicitly set aside, not silently
dropped:
- **Snooze/Archive buttons are decorative** (`ThreadPanel.tsx:432-440`, no
  `onClick`) — real gap, but needs a new `snoozed_until`/`archived`
  message-state column + endpoint; bigger than one sprint's worth of "small,
  reversible, no new architecture." Separate future board.
- **Search icon is decorative, no FTS backend exists** — P2 in the master
  brief's brainstorm table, larger scope (backend full-text search + UI),
  not picked this sprint.
- **MFA for admin paths** — genuine open Security Gate P0 line, but building
  it now means inventing an admin surface just to gate it. Flagged for an
  explicit user decision rather than picked up autonomously; not attempted.

## Scope decision

Built the literal requirement, not more:

- Show an onboarding screen when the inbox is genuinely empty AND no
  built-in source is configured yet AND the user hasn't skipped it before.
- "Skip" must not block the user forever — dismissal persists (localStorage,
  survives across sessions, unlike the existing sessionStorage-based
  mode/filter persistence) and the screen never reappears after Skip.
- **Deliberate simplification, stated explicitly rather than silently
  assumed:** the gating check does not separately query whether a Generic
  HTTP Connector has been registered (it would need its own one-off fetch
  purely to inform a dismissal heuristic). A registered-but-unsynced generic
  connector with zero messages will still show onboarding once — harmless
  (Skip or an arriving message both resolve it permanently for that path).
  If this proves annoying in practice, add the extra check then, not now.
- The screen does not try to let the user actually enter secrets or create a
  connector inline — both "action" buttons just switch to Settings, where
  the already-built, already-tested `SettingsPanel`/`GenericConnectorsPanel`
  flows take over. No duplicated logic, no new write surface.

## What was built

- `frontend/src/components/OnboardingScreen.tsx` (new): full-content-area
  view (same layout shape as `SecurityCenter`/`SettingsPanel`), explains why
  a source is needed, two cards (built-in sources → env-var setup is
  backend-only, matching the existing security model; custom HTTP/webhook
  source → no secret needed for `auth_method: none`), both linking to
  Settings, plus a "Skip for now" link. Coded against existing CSS custom
  properties only, no hardcoded colors/radii, `aria-label` on the skip
  action, `role="region"` container — per `CLAUDE.md` §6.
- `frontend/src/app/page.tsx`:
  - New `onboardingSkipped` state, SSR-safe default `false`, restored from
    `localStorage` in its own mount-only effect — same pattern (and same
    reason: avoiding a React hydration mismatch, see the Sprint 11 lesson in
    `CURRENT_STATE.md`) as the existing mode/filters `sessionStorage`
    restoration, just a different storage API since this needs to survive
    across sessions, not just the tab.
  - `showOnboarding` derived from: `mode === "normal"` (don't fight explicit
    navigation to Settings/Security Center), not skipped, capabilities
    actually loaded (`connectorsLastUpdatedAt !== null`, avoids a flash
    before the first fetch resolves), inbox empty (`totalCount === 0`), and
    no built-in capability `configured`.
  - Rendered alongside the existing `mode === "security"`/`mode ===
    "settings"` full-view branches; the normal 3-pane layout's render
    condition gained `&& !showOnboarding`.

## Verified

- `tsc --noEmit`: clean. `npm run build`: success.
- **Live browser verification** (real backend + real frontend, sandboxed
  browser tool via `host.docker.internal:8000`/`:3000`): against a genuinely
  empty scratch DB (no connectors configured, zero messages) the onboarding
  screen rendered automatically on first load. "View setup instructions"
  and "Create a custom connector" both correctly switch to Settings.
  Navigating back to Inbox (still empty, still not skipped) shows onboarding
  again — confirms it isn't a one-shot-per-page-load fluke. "Skip for now"
  correctly hides it and shows the normal empty-inbox state.
  **Specifically checked for the Sprint 11 hydration-mismatch bug class**
  (a `useState` initializer reading storage synchronously): reloaded the
  page with the skip flag already persisted in `localStorage` — zero console
  errors, onboarding correctly stayed hidden post-reload. Also verified the
  other suppression path: seeded 5 real messages via the existing `/seed`
  endpoint, cleared the skip flag, reloaded — onboarding correctly did not
  appear once `totalCount > 0`, independent of the skip flag. Zero
  unexpected console errors across every step (0 total messages logged,
  including no favicon 404 this time).
- Verification processes stopped via `taskkill //PID ... //F` (netstat-
  confirmed clean); `frontend/.env.local` reverted to
  `http://localhost:8000` and rebuilt; scratch DB removed before ending the
  session.

## No backend changes

Pure frontend feature reusing existing, already-tested endpoints
(`/connectors/capabilities`, inbox fetch). Backend suite unchanged (267
passed).
