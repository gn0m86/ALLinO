# Handoff: Secure Unified Inbox

## Overview
A secure, privacy-first **unified inbox** web app that brings **Email, Slack, and Telegram** into one calm, high-trust workspace. The design goal is a quiet, highly legible UI with clear hierarchy, no loud colors, and no visual noise — built so it never provokes unnecessary data collection.

This package contains everything needed to implement the design in a real codebase.

## About the Design Files
The files in this bundle are **design references created in HTML** — a prototype showing the intended look, structure, and behavior. **They are NOT production code to copy directly.**

Your task is to **recreate these designs in your target codebase's environment** (React, Vue, Svelte, SwiftUI, etc.), using its established patterns, component library, and conventions. If no front-end environment exists yet, choose the most appropriate framework for the project and implement there.

- `secure-inbox-spec.html` — open in any browser (double-click; no server, no dependencies). The **top section is the live concept screen**; below it are six documented spec sections (Tokens, Components, States, Responsive, Accessibility & Privacy, React+Tailwind code). Use the switcher at the top to preview the 3 directions × light/dark.
- `tokens.css` — all design tokens as ready-to-use CSS custom properties (3 directions × light/dark + auto OS dark). Drop straight into your app.
- `source/` — the original authoring file (`.dc.html`). Reference only; it needs a proprietary runtime and will not render standalone. Ignore unless curious.

## Fidelity
**High-fidelity (hifi).** Final colors, typography, spacing, radii, shadows, and interaction states are all specified. Recreate the UI pixel-accurately using your codebase's libraries. Exact values are in `tokens.css` and in the tables below.

## Visual Directions (pick ONE for production)
The prototype ships **three interchangeable calm directions**; they share the same layout and token *names*, differing only in token *values*. Choose one as your product theme. All three pass WCAG AA.
- **Quiet Slate** *(recommended default)* — cool neutrals, slate-blue accent, Public Sans throughout, medium radii.
- **Warm Paper** — warm off-white neutrals, Newsreader serif headings, softer/larger radii.
- **Graphite** — pure-gray neutrals, tight radii, most utilitarian.

Each has a **light and dark** theme. Switch via attributes on a root element: `<html data-direction="slate" data-theme="light">`. With no `data-theme`, the OS preference applies (see `tokens.css`).

---

## Screens / Views

### 1. Main Inbox (three-pane)
**Purpose:** Triage and reply to messages from all sources in one place.

**Layout (desktop ≥1100px):** horizontal flex, full viewport height.
- **Nav rail** — fixed `218px`. Padding `16px 12px`. Logo + lockup at top; primary nav (Inbox / Starred / Snoozed / Archive); a "Sources" group (Email / Slack / Telegram with counts); account chip pinned to bottom showing an "Encrypted" status.
- **Message list** — fixed `382px`, `1px solid var(--border)` right divider. Header (title "Inbox", unread count, search + filter icon buttons), then a scrolling list of inbox items.
- **Thread panel** — flexes to fill remaining width, background `var(--bg)`. Sticky header (avatar, subject, channel/source meta, snooze/archive/more actions) → scrolling message stream with the **Security Card** pinned above it → sticky composer at the bottom.

**Responsive:**
- **Tablet 720–1099px:** nav collapses to an icon rail; list + thread share width.
- **Mobile <720px:** single pane. List and thread swap full-screen (tap a row → thread; back → list). ⌘K becomes a bottom search affordance. All hit targets ≥ 44px.

### 2. Command Palette (overlay)
**Purpose:** keyboard-first navigation and actions. Opens on **⌘K**.
**Layout:** centered dialog, `min(560px, 92%)` wide, `72px` from top, over a `var(--overlay)` scrim. Search input row → grouped results (Jump to / Actions / Privacy) → footer with nav hints and an "Runs on-device" reassurance. Radius `var(--r-panel)`, shadow `var(--shadow-3)`. Entrance: 140ms fade+rise (disabled under reduced-motion).

---

## Components

### Inbox Item (list row — render as a `<button>`)
Row carries six signals without crowding. Padding `15px 16px` (comfortable) — use `10px 12px` for a compact density option. Radius `var(--r-card)`. Layout: `display:flex; gap:12px`.
- **Selection bar:** absolutely-positioned `3px` wide bar on the left edge, `var(--accent)` when the row is selected, else transparent. (`top/bottom: 11px`, radius `0 3px 3px 0`.)
- **Avatar block (flex:none):** `38×38` rounded square (`var(--r-card)`), `var(--surface-3)` bg, initials in `13px/600 var(--text-2)`. Overlaid bottom-right: a `17×17` **source badge** (rounded `6px`, `2px solid var(--surface)` ring, source-soft bg, source-color icon).
- **Body (flex:1, min-width:0, column, gap:3px):**
  - Line 1: sender name (`14px`, weight **700 if unread** else 500, truncates) · spacer · time (`11px var(--font-mono) var(--text-3)`) · `7px` accent unread dot (only if unread).
  - Line 2: optional channel chip (`#channel`, `11px` mono, source-color on source-soft, radius `5px`) + subject (`14px`, weight 600 if unread else 500, truncates).
  - Line 3: optional redacted-eye icon + snippet (`13px var(--text-2)`, truncates) + optional attachment icon + **priority badge** (only Urgent/High).
- **States:** hover → row bg `var(--surface-2)` (no motion/shift). focus-visible → `2px solid var(--accent)` outline, `2px` offset. selected → bg `var(--surface-2)` + accent bar.
- **a11y:** `aria-label="{sender}: {subject} (unread)"`. Use `role="list"`/`role="listitem"`; roving tabindex for arrow-key nav.

### Source Badge
Identifies origin; **desaturated on purpose — identify, never shout.** `inline-flex`, `gap:6px`, radius `999px`, padding `5px 11px` (full) or `17×17` icon-only (in list). Always **icon + text** so color is never the only cue.
- Email → `--src-email` on `--src-email-soft`, mail icon.
- Slack → `--src-slack` (muted plum) on `--src-slack-soft`, hash icon.
- Telegram → `--src-telegram` (muted steel) on `--src-telegram-soft`, paper-plane icon.

### Priority Badge
`inline-flex`, `gap:6px`, radius `999px`, `font-mono 10.5–11px`, a `5–6px` leading dot in the same color. **Only Urgent and High render a colored pill in the list** (keeps the list calm); Normal/Low render nothing in the list (or a neutral chip in detail views).
- **Urgent** → `--danger` on `--danger-soft`.
- **High** → `--warning` on `--warning-soft`.
- **Normal** → `--text-2` on `--surface-3` (detail views only).
- **Low** → `--text-3`, transparent bg, `1px solid var(--border)` (detail views only).

### Thread Panel
Three stacked zones in a column:
1. **Header** (sticky): source icon tile, subject (`16.5px` head font, head weight/tracking), meta line (`12px var(--text-3)` — channel/people/source), action icon buttons (snooze/archive/more, each `32×32`, `1px solid var(--border)`, radius `var(--r-btn)`).
2. **Stream** (scrolls): the Security Card first, then messages. Each message: `32×32` round avatar (`flex:none`) + body. **Your own messages** tint avatar/name with `--accent` / `--accent-soft`; others use `--surface-3` / `--text`. Name `13.5px/600`, time `11px` mono, body `14px/1.55 var(--text-2)`, `max-width:62ch`.
3. **Composer** (sticky bottom): bordered card, "Reply securely…" placeholder, attach button, an **always-visible "End-to-end encrypted"** label, and a primary Send button with `⌘↵` hint.

### Command Palette
See Screen 2. Result row: `26×26` icon tile + label (`13.5px`) + optional scope chip (e.g. `source`, `on`) + optional shortcut key (`E`, `⌘↵`) in a `var(--surface-3)` mono key-cap. Active row: bg `var(--accent-soft)`, label/icon `var(--accent)`. Footer states **"Runs on-device"** — search/commands must not emit query telemetry.

### Security Card
Builds trust at a glance — calm, never alarmist. Bordered card (`var(--border)`, radius `var(--r-card)`, `var(--shadow-1)`).
- **Header:** `24×24` shield-check tile in `--success-soft`/`--success` + "Conversation secured" (`13.5px/600`) + optional source chip.
- **Body:** a `2×2` grid (`<dl>`) of four facts, hairline-divided. Each: mono `10px` uppercase label (`var(--text-3)`) over a `12.5px var(--text)` value:
  - **Transport** — e.g. "TLS 1.3 · in transit"
  - **Identity** — e.g. "SSO · members verified"
  - **Content** — e.g. "Remote media blocked"
  - **Retention** — e.g. "Auto-deletes in 30 days"
- **Footer (optional):** privacy footnote ("Previews stay on your device. No read receipts are sent.") + a "Privacy details ›" link.

---

## Interactions & Behavior
- **Open thread:** click/Enter on an inbox row → loads thread in panel (mobile: full-screen). Selected row shows accent bar + `surface-2`.
- **Command palette:** ⌘K opens; Esc/scrim-click closes; ↑/↓ move; Enter runs. Click the scrim closes; clicks inside do not (`stopPropagation`).
- **Theme/direction:** set `data-direction` + `data-theme` on root; everything re-derives from CSS vars with no re-render.
- **Hover:** surfaces shift to `--surface-2`; **no motion, no layout shift.**
- **Loading:** inline spinner (`om-spin`, .7s linear) + "Syncing sources…"; buttons swap label to "Sending…" with a spinner and stay disabled.
- **Skeleton:** mirror the real row geometry (38px avatar block + two text bars) using a shimmer gradient (`om-shimmer`, 1.4s). Must respect reduced-motion.
- **Error (field):** `1.5px solid var(--danger)` input border + trailing alert icon + helper text **with an icon** (never color-only). 
- **Error (system):** inline banner on `--danger-soft` with alert icon, title, and a calm recovery line ("We'll retry automatically. Nothing was sent twice.").
- **Transitions/animations:** entrance fade+rise 140ms; spinners as above. Everything collapses to ~0ms under `prefers-reduced-motion`.

## State Management
- `direction: 'slate' | 'paper' | 'graphite'`, `theme: 'light' | 'dark'` (persist; default slate/light or OS).
- `density: 'comfortable' | 'compact'` (row padding).
- `selectedThreadId` — drives list selection + thread panel; on mobile also drives list↔thread view swap.
- `paletteOpen: boolean` (⌘K).
- Per-message: `unread`, `priority`, `source`, `channel?`, `attachment?`, `redacted?`.
- Data fetching: sync state per source (idle/loading/error) feeding the loading + system-error states. **Privacy:** search/commands run on-device — no query goes to a server.

## Design Tokens
**All values live in `tokens.css`** (3 directions × light/dark). Token *names* are stable across directions — code against the names, not the hexes. Summary of names:
- **Surfaces:** `--bg`, `--surface`, `--surface-2`, `--surface-3`
- **Lines/text:** `--border`, `--border-strong`, `--text`, `--text-2`, `--text-3`
- **Accent (single):** `--accent`, `--accent-hover`, `--accent-soft`, `--accent-ring`, `--accent-fg`
- **Status (desaturated):** `--success(-soft)`, `--warning(-soft)`, `--danger(-soft)`, `--info(-soft)`
- **Sources:** `--src-email(-soft)`, `--src-slack(-soft)`, `--src-telegram(-soft)`
- **Elevation:** `--shadow-1` (resting card), `--shadow-2` (floating screen), `--shadow-3` (palette/modal)
- **Skeleton:** `--skeleton`, `--skeleton-sheen`; **Overlay:** `--overlay`
- **Radius:** `--r-chip`, `--r-btn`, `--r-card`, `--r-panel`
- **Type:** `--font-ui`, `--font-head`, `--font-mono`, `--head-weight`, `--head-tracking`
- **Spacing scale (4px base):** 4, 8, 12, 16, 20, 24, 32, 40.

**Quiet Slate / light reference hexes:** bg `#F4F6F9`, surface `#FFFFFF`, surface-2 `#F0F3F7`, surface-3 `#E7ECF2`, border `#E4E8EF`, border-strong `#D2D9E2`, text `#172230`, text-2 `#525F6F`, text-3 `#8A95A4`, accent `#2F4A6B`, accent-hover `#243B57`, accent-soft `#E8EDF4`, accent-fg `#FFFFFF`, success `#2E7D58`, warning `#8A6A1E`, danger `#B04242`, info `#355C86`.

### Typography
- **UI / headings:** Public Sans (Warm Paper uses **Newsreader** serif for headings only).
- **Technical labels / meta / shortcuts:** IBM Plex Mono.
- **Scale:** Display 46/1.06 · Title 19/1.2 · Subtitle 16.5/1.3 (600) · Body 14/1.55 (400) · Label 13/1.4 (500) · Caption 12/1.4 · Mono 11/1.4 (500). Headings use `--head-weight` + `--head-tracking`.
- Fonts via Google Fonts (Public Sans, Newsreader, IBM Plex Mono) — or self-host equivalents.

### Tailwind mapping
Map tokens in `tailwind.config` so utilities like `bg-surface`, `text-accent`, `rounded-card`, `shadow-1` work. See the **"React + Tailwind"** section in `secure-inbox-spec.html` for a ready `tailwind.config.ts` plus `InboxItem.tsx`, `Badges.tsx`, and `SecurityCard.tsx` reference snippets.

## Accessibility (WCAG AA — required)
- Text contrast meets AA in all directions/themes (Primary 16:1, Secondary 6.5:1, Tertiary/large 3:1+). The spec page computes ratios live.
- **2px visible focus ring** (`--accent` / `--accent-ring`) with 2px offset on every interactive element.
- **Never color-only:** source + priority + error always pair color with icon/text.
- Full keyboard path: ⌘K palette, arrow nav, `E`/`S` shortcuts, roving tabindex in the list.
- Semantic roles: `list`/`listitem` rows, `dialog` palette, `aria-live` for sync + errors.
- Respect `prefers-reduced-motion` and `prefers-color-scheme`.
- Hit targets ≥ 44px on touch.

## Privacy-first principles (product requirement)
1. **Remote images & trackers blocked by default** — opt in per sender, never globally.
2. **On-device search & command palette** — no query telemetry.
3. **No read receipts** unless explicitly enabled; previews can be redacted.
4. **Data minimization** — ask for the least the moment needs; clear retention + one-tap local cache wipe. Don't add fields/permissions the feature doesn't require.

## Assets
- **Icons:** simple line icons (stroke 1.7–1.9, round caps/joins) drawn inline as SVG in the prototype. Replace with your icon library (e.g. Lucide/Heroicons) — equivalents: shield, shield-check, mail, hash, paper-plane (send), inbox, clock, archive, star, search, filter, paperclip, eye-off, alert-circle/triangle, spinner.
- **Fonts:** Public Sans, Newsreader, IBM Plex Mono (Google Fonts).
- **Images:** none — avatars are initials on `--surface-3`. No raster assets to ship.
- No third-party brand assets are used; Slack/Telegram are represented by neutral generic glyphs, not their official logos. Use your own/licensed marks if you need official branding.

## Files
- `secure-inbox-spec.html` — the full visual design reference (open in a browser).
- `tokens.css` — design tokens, ready to import.
- `source/Secure Inbox — Concept & Spec.dc.html` — original authoring file (reference only; won't render standalone).
