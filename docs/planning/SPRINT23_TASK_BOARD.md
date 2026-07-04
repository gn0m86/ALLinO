# Sprint 23 — Snooze duration picker

Opened: 2026-07-03. Closed: 2026-07-03.

## Context

User delegated again ("продолжай"). Sprint 22's board explicitly listed this
as one of two immediate follow-ups. Picked over "view archived"/unarchive
because it's strictly smaller: the backend `POST .../snooze` endpoint
already accepts an optional `{"hours": n}` body (added in Sprint 22 for
exactly this future use) — this sprint is frontend-only, no migration, no
new endpoint, no new permission surface. "View archived" would need a new
backend list endpoint/query param plus an unarchive mutation; left open.

## Scope decision

- Clicking the Snooze icon button now opens a small dropdown menu with four
  fixed options (1 hour / 4 hours / Tomorrow, 9 AM / Next week) instead of
  immediately snoozing for a hardcoded 4h. Picking an option calls the
  existing endpoint with that duration.
- **Deliberately four fixed options, not a free-form time/date picker** —
  matches the "smallest useful thing" bar from Sprint 22's own framing of
  the 4h default; a full custom-datetime picker is a separate, bigger
  component if ever needed.
- No backend change at all — the `hours` override already existed.

## What was built

- `frontend/src/lib/api.ts`: `snoozeMessage()` gains an optional `hours`
  parameter, sent as the JSON body when provided (previously always sent no
  body, relying on the backend's own default).
- `frontend/src/components/ThreadPanel.tsx`:
  - New `snoozeOptions()` helper computing the four choices; `"Tomorrow, 9
    AM"` is computed as hours-until-next-day-9AM from `Date.now()`, not a
    hardcoded number.
  - `handleSnooze(hours: number)` now takes the duration explicitly instead
    of always using the backend default.
  - The Snooze button no longer snoozes directly on click — it toggles a
    `role="menu"` dropdown (`aria-haspopup`/`aria-expanded` on the trigger,
    `role="menuitem"` on each option), closed by picking an option, by
    clicking the just-added full-viewport transparent backdrop, or when the
    open thread changes (extended the existing item-change reset `useEffect`
    used for `actionPending`/`actionError`).
  - Button `aria-label` changed from `"Snooze for 4 hours"` to plain
    `"Snooze"` since it's now a menu trigger, not a single fixed action.
- `frontend/src/app/globals.css`: new `.menu-item:hover`/`:focus-visible`
  rules (inline styles can't express `:hover`; every other interactive
  element in this codebase that needs a hover state already goes through a
  shared CSS class the same way, e.g. `.icon-btn`).

## Verified

- No backend changes, so the existing backend suite is unaffected by
  construction — re-ran it anyway as a sanity check: `pytest -q` => 277
  passed (unchanged from Sprint 22).
- Frontend: `tsc --noEmit` clean; `npm run build` success.
- **Live browser verification** (real backend + real frontend, sandboxed
  browser tool via `host.docker.internal:8000`/`:3000`): seeded 5 messages,
  opened one, clicked Snooze -- menu opened with all 4 options positioned
  correctly within the viewport (checked via `browser_snapshot(boxes:
  true)`), zero console errors. Picked "Tomorrow, 9 AM" -- inbox count went
  5 -> 4, message vanished, thread reset; cross-checked the audit log
  directly against the backend and confirmed `snoozed_until` was computed as
  the actual next-day 9 AM timestamp, not a placeholder. Opened another
  message, opened the menu again, then clicked outside it (via
  `document.elementFromPoint` + a dispatched click, since Playwright's
  strict-actionability check correctly refused to punch through the
  backdrop on a normal click -- which itself confirmed the backdrop
  actually intercepts pointer events as designed) -- confirmed the menu
  closed **without** triggering a snooze (inbox count stayed at 4, no
  audit entry added). Verification processes cleaned up, `.env.local`
  reverted, scratch DB removed.

## Explicitly still open

"View archived"/unarchive UI and the Sprint 21 Search/MFA candidates —
unchanged by this sprint.
