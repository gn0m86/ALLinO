# SecureInbox — Design Concept & UI Specification
*Design Director + Senior UI Engineer brief · v1.0 · June 2026*

---

## 1. Design Intent

### Product Statement
SecureInbox aggregates email, Slack, GitHub, Linear, and other message sources into one
reading-first surface where **data provenance is always visible** and users remain in full
control of what is shared and with whom.

**Audience:** Privacy-conscious professionals — security researchers, compliance officers,
senior developers, remote-first teams operating across high-trust environments.

**Single job of the interface:** Let users read and act on messages with confidence that no
data is leaking and no engagement is being silently tracked.

---

### Aesthetic Direction

**Cool-neutral authority.** Not warm cream (personal-blog feel), not dark-with-acid-accent
(hacker-tool feel). A cool gray-white base that reads as *institutional trust*, with a
slate-indigo accent that signals "interactive" without demanding attention.

The deliberate aesthetic risk: **typography as identity.** `DM Sans` at tight tracking and
precise optical sizing — not Inter, not SF Pro. It reads as slightly technical and unhurried
simultaneously. Paired with `DM Mono` for all cryptographic metadata, timestamps, and IDs,
this creates a strong visual separation between *message content* (humanistic) and *system
metadata* (machine-legible).

---

### The Signature Element: Trust-Lines

Every inbox item carries a **2px vertical rule** on its left edge. This rule encodes
encryption and data-handling status through **line style** — not color alone (color-blind
accessible):

| Line style | Meaning | Color |
|---|---|---|
| Solid `—` | End-to-end encrypted, origin verified | `secure-500` `#1A8A70` |
| Dashed `- -` | In transit / partial encryption | `warn-500` `#C2600A` |
| Dotted `···` | Unknown source or no encryption | `ink-300` `#A0AABB` |

This gives users **peripheral security awareness** without interrupting reading flow. It is
the one thing this inbox will be remembered for.

---

### Privacy-First Design Principles

1. **Default to minimal display.** Sender photos render as initials-only unless explicitly
   opted in. No email-address-to-avatar lookups. No remote asset fetches by default.
2. **Make data provenance visible.** Every message shows origin, which systems handled it,
   and retention period — accessible via the Privacy Audit Trail.
3. **Never collect engagement silently.** Read receipts are opt-in and visibly flagged
   when active.
4. **Reduce attack surface.** External images are blocked by default. Link previews are
   opt-in. Attachments display metadata before download.
5. **Absence of badge is information.** No badge = Normal priority. No noise for the 90%
   case.

---

## 2. Design Tokens

### 2.1 Color System

#### Full Palette Definition

```css
:root {
  /* ── Canvas ─────────────────────────────────────────── */
  --color-canvas:          #FFFFFF;
  --color-canvas-subtle:   #F4F6F8;   /* page background — cool, not warm */
  --color-canvas-inset:    #ECEEF2;   /* sidebar, recessed areas           */

  /* ── Ink (text hierarchy) ────────────────────────────── */
  --color-ink-950:  #0D1117;  /* headings, maximum contrast  */
  --color-ink-800:  #1E2432;  /* body text                   */
  --color-ink-600:  #4A5568;  /* secondary text              */
  --color-ink-400:  #8896A8;  /* placeholders, muted labels  */
  --color-ink-300:  #A0AABB;  /* trust-line: unknown         */
  --color-ink-200:  #C5CED8;  /* dividers, borders           */
  --color-ink-100:  #E4E8EE;  /* hover fill, subtle bg       */
  --color-ink-50:   #F4F6F8;  /* off-white surfaces          */

  /* ── Accent — Slate-Indigo (interactive) ─────────────── */
  --color-accent-800: #1E2A7A;
  --color-accent-700: #2D3A8C;  /* primary buttons, links  */
  --color-accent-600: #3B4BA3;  /* hover                   */
  --color-accent-400: #7B89D4;  /* focus rings             */
  --color-accent-100: #EEF0FB;  /* accent tint background  */
  --color-accent-50:  #F5F6FD;  /* lightest accent surface */

  /* ── Secure — Teal-Emerald (encryption / verified) ──── */
  --color-secure-700: #0F5E4D;
  --color-secure-500: #1A8A70;  /* trust-line: encrypted */
  --color-secure-300: #5CB89B;
  --color-secure-100: #E4F5F0;
  --color-secure-50:  #F0FAF7;

  /* ── Warn — Amber-Ochre ──────────────────────────────── */
  --color-warn-700: #9A4E0A;
  --color-warn-500: #C2600A;   /* trust-line: partial */
  --color-warn-100: #FDF0E6;

  /* ── Danger — Deep Red ───────────────────────────────── */
  --color-danger-700: #9B1C1C;
  --color-danger-500: #C42B2B;
  --color-danger-100: #FDF0F0;

  /* ── Source badges (muted monochrome) ────────────────── */
  --color-source-email:  #2D3A8C;   /* slate-indigo  */
  --color-source-slack:  #4A1C6B;   /* muted purple  */
  --color-source-github: #1A2332;   /* near-black    */
  --color-source-linear: #1A3B5C;   /* muted navy    */
  --color-source-other:  #3D4458;   /* neutral slate */
}
```

#### Contrast Ratios (WCAG AA)

| Foreground → Background | Ratio | Level |
|---|---|---|
| `ink-950` on `canvas` | 19.1 : 1 | **AAA** |
| `ink-800` on `canvas` | 12.6 : 1 | **AAA** |
| `ink-600` on `canvas` | 5.8 : 1 | **AA** |
| `ink-400` on `canvas` | 3.5 : 1 | AA large text only |
| `accent-700` on `canvas` | 7.4 : 1 | **AA** |
| `accent-700` on `accent-100` | 6.1 : 1 | **AA** |
| `secure-700` on `canvas` | 8.2 : 1 | **AAA** |
| `danger-500` on `canvas` | 5.1 : 1 | **AA** |
| `warn-700` on `canvas` | 7.6 : 1 | **AA** |

> **Rule:** Never use `ink-400` for body text. Large-text or decorative use only.

---

### 2.2 Typography

#### Font Stack

```css
:root {
  --font-ui:   'DM Sans', ui-sans-serif, system-ui, sans-serif;
  --font-mono: 'DM Mono', 'Cascadia Code', 'JetBrains Mono', monospace;
}
```

Google Fonts import:
```css
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:ital,wght@0,400;0,500;1,400&display=swap');
```

#### Type Scale

| Token | Size | Line-height | Tracking | Weight | Usage |
|---|---|---|---|---|---|
| `text-2xl` | 1.5rem / 24px | 2rem | −0.025em | 600 | Panel headings |
| `text-xl` | 1.25rem / 20px | 1.75rem | −0.02em | 600 | Thread subject |
| `text-lg` | 1.0625rem / 17px | 1.625rem | −0.01em | 500 | Section titles |
| `text-base` | 0.9375rem / 15px | 1.5rem | −0.005em | 400 | Body text |
| `text-sm` | 0.8125rem / 13px | 1.25rem | 0em | 400/500 | UI labels, inbox items |
| `text-xs` | 0.6875rem / 11px | 1rem | +0.02em | 400 | Badges, captions |
| `text-mono-sm` | 0.75rem / 12px | 1.125rem | 0em | 400 | DM Mono — timestamps |
| `text-mono-xs` | 0.6875rem / 11px | 1rem | 0em | 400 | DM Mono — hashes, IDs |

#### Font Weight Usage

| Weight | Usage |
|---|---|
| 400 Regular | Body text, metadata, muted content |
| 500 Medium | UI labels, secondary headings, sender (read) |
| 600 SemiBold | Headings, sender name (unread), badge text |
| 700 Bold | Unread count, critical alert numbers only |

---

### 2.3 Spacing (4px Grid)

All values are strict multiples of 4px.

```js
// tailwind.config.ts — spacing
spacing: {
  '0.5': '2px',   // micro: icon gaps
  '1':   '4px',   // xs: tight internal padding
  '1.5': '6px',   // badge vertical padding
  '2':   '8px',   // sm: badge horizontal padding
  '2.5': '10px',
  '3':   '12px',  // inbox item vertical padding (compact)
  '4':   '16px',  // inbox item horizontal padding
  '5':   '20px',  // inbox item vertical padding (comfortable)
  '6':   '24px',  // panel header padding
  '8':   '32px',  // section gaps
  '10':  '40px',
  '12':  '48px',
  '16':  '64px',
}
```

#### Component Spacing Reference

| Context | Padding |
|---|---|
| InboxItem (compact) | `12px 16px` |
| InboxItem (comfortable) | `16px 20px` |
| Badge | `3px 7px` (v / h) |
| Button sm | `6px 12px` |
| Button default | `8px 16px` |
| Panel header | `20px 24px` |
| ThreadPanel body | `20px 24px` |
| CommandPalette input row | `12px 16px` |

---

### 2.4 Border Radius

```js
borderRadius: {
  'none': '0px',    // inbox items (span full width, no rounding)
  'sm':   '3px',    // badges, tags, small chips
  'md':   '6px',    // inputs, cards, dropdowns
  'lg':   '10px',   // panels, popovers
  'xl':   '16px',   // command palette, modals
  'full': '9999px', // avatars, toggle pills
}
```

**Design rule:** Use the smallest radius that feels intentional. Inbox items use `radius-none`
(span full width). Floating surfaces use `radius-xl`. Squareness on dense surfaces reads as
precision, not coldness.

---

### 2.5 Shadows (Elevation System)

No dramatic drop shadows. Elevation is communicated through background contrast and hairline
borders. Shadows are present but restrained.

```css
:root {
  /* Elevation 0 — flat (list rows, inline elements) */
  --shadow-0: none;

  /* Elevation 1 — card separation */
  --shadow-1:
    0 1px 3px 0   rgba(14, 18, 27, 0.06),
    0 1px 2px -1px rgba(14, 18, 27, 0.04);

  /* Elevation 2 — floating panels, dropdowns, popovers */
  --shadow-2:
    0 4px 12px 0   rgba(14, 18, 27, 0.10),
    0 2px 4px -1px rgba(14, 18, 27, 0.06),
    0 0 0 1px      rgba(14, 18, 27, 0.04);

  /* Elevation 3 — command palette, modal dialogs */
  --shadow-3:
    0 16px 48px -8px rgba(14, 18, 27, 0.18),
    0 4px 16px -4px  rgba(14, 18, 27, 0.10),
    0 0 0 1px        rgba(14, 18, 27, 0.06);

  /* Focus ring — not a shadow, documented here for completeness */
  --focus-ring: 0 0 0 2px #FFFFFF, 0 0 0 4px #7B89D4;
}
```

---

### 2.6 Animation & Motion

```css
:root {
  --duration-instant: 80ms;
  --duration-fast:    150ms;
  --duration-base:    200ms;
  --duration-slow:    300ms;

  --ease-out:    cubic-bezier(0.16, 1, 0.3, 1);    /* snappy settle */
  --ease-in-out: cubic-bezier(0.45, 0, 0.55, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1); /* slight overshoot */
}

/* Mandatory reduced-motion override */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration:        0.01ms !important;
    animation-iteration-count: 1      !important;
    transition-duration:       0.01ms !important;
    scroll-behavior:           auto   !important;
  }
}
```

#### Motion Inventory

| Element | Duration | Easing | Note |
|---|---|---|---|
| Hover background (InboxItem) | 150ms | ease-out | Background only, no layout shift |
| Panel slide-in (tablet/mobile) | 300ms | ease-out | `translateX` |
| CommandPalette appear | 200ms | ease-out | Opacity + `scale(0.97 → 1)` |
| Skeleton shimmer | 1.5s | ease-in-out infinite | Static in `prefers-reduced-motion` |
| Priority Critical pulse | 2s | ease-in-out infinite | Static in `prefers-reduced-motion` |
| Trust-lines | **none** | — | Security indicators must be instant |
| NavRail collapse | 200ms | ease-out | Width transition only |

---

## 3. Component Library

### 3.1 InboxItem

The core list unit. Encodes: trust level, source, sender, subject, preview, time, read
state, and priority in a single compact row.

#### Anatomy

```
┌─────────────────────────────────────────────────────────────────┐
│║  [Avatar]  Sender Name        [SourceBadge] [PriorityBadge]  ●│
│║            Subject line (semibold when unread)          HH:MM  │
│║            Preview text — one line, truncated with ellipsis…   │
└─────────────────────────────────────────────────────────────────┘
 ↑
 2px trust-line (solid / dashed / dotted, semantic color + pattern)
```

#### State Table

| State | Background | Trust-line | Sender weight | Preview opacity | Notes |
|---|---|---|---|---|---|
| Read | `canvas` | per trust | 400 | 60% | Default |
| Unread | `canvas` | per trust | 600 | 80% | Unread dot visible |
| Hover | `ink-100` | per trust | unchanged | unchanged | 150ms transition |
| Selected | `accent-50` | `accent-700 solid` | 600 | 90% | Keyboard or click |
| Focus-visible | `canvas` + focus ring | per trust | unchanged | unchanged | Ring only, no bg |
| Disabled | `ink-50` | `ink-200 solid` | 400, `ink-400` | 40% | Non-interactive |
| Error | `danger-100` | `danger-500 solid` | 400 | 80% | Sync/fetch failure |
| Loading | skeleton | `ink-200 solid` | — | — | Shimmer animation |

**Avatar:** 32×32px circle, initials only (first character of sender name), `bg-ink-100
text-ink-600`. Never fetches a remote avatar URL without explicit opt-in.

---

### 3.2 SourceBadge

Small monochrome pill indicating message origin. Intentionally low-contrast — source
identity is contextual, not primary information.

```
 [ ✉ Email ]  [ ◆ Slack ]  [ ◎ GitHub ]  [ ■ Linear ]
```

| Property | Value |
|---|---|
| Background | `source-color / 10%` opacity |
| Text | `source-color` at 100% |
| Font | DM Sans 11px / 500 / tracking +0.02em |
| Padding | `3px 7px` |
| Radius | `sm` (3px) |
| Max-width | `80px` with text truncation |
| Icon | 12px, source-specific glyph |

**Rule:** Never use bright brand colors. All badges stay within the muted source palette
defined in the token system. The badge should not compete with message content.

---

### 3.3 PriorityBadge

Encodes urgency. Used sparingly — most messages show no badge.

| Priority | Badge | Color | Icon | Additional |
|---|---|---|---|---|
| Critical | `CRITICAL` | `danger-700` on `danger-100` | `◉` | Pulse animation (2s) |
| High | `HIGH` | `warn-700` on `warn-100` | `▲` | Static |
| **Normal** | **(none)** | — | — | Absence = Normal |
| Low | `LOW` | `ink-400` on `ink-100` | `▽` | Static |

**Critical pulse keyframe:**
```css
@keyframes priority-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}
.priority-critical-icon {
  animation: priority-pulse 2s ease-in-out infinite;
}
@media (prefers-reduced-motion: reduce) {
  .priority-critical-icon { animation: none; }
}
```

---

### 3.4 ThreadPanel

Right-side detail panel. Slides in from right on tablet/mobile; immediate on desktop.

#### Layout Anatomy

```
┌────────────────────────────────────────────────────────────────┐
│  ← Back         [SecurityCard icon button]                 ⋯  │  56px header
├────────────────────────────────────────────────────────────────┤
│  Anna K.                                          14:32 · Mon  │
│  To: you@domain.com                                            │
│  Subject here — large, 20px semibold                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ⚠ External images blocked to protect your privacy.  [Show]   │
│                                                                │
│  Message body rendered as sanitized text.                      │
│  Markdown tables, links, code blocks supported.               │
│  No remote asset loading without explicit user action.         │
│                                                                │
│  [📎 spec.pdf  42 KB]  [📎 screenshot.png  180 KB]            │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  PRIVACY AUDIT TRAIL                                      ↕    │  collapsible
│  ────────────────────────────────────────────────────────────  │
│  ●  Encrypted            E2E · TLS 1.3                         │
│  ●  Origin verified      SPF ✓ · DKIM ✓ · DMARC ✓            │
│  ○  Tracking pixels      2 blocked                             │
│  ○  Read receipt         Not sent                              │
│  ────────────────────────────────────────────────────────────  │
│  Provider: Gmail · Retention: 90 days                          │
│  Hash: a3f4…c91d                            [DM Mono]          │
└────────────────────────────────────────────────────────────────┘
```

**Privacy Audit Trail** is collapsed by default. It expands on click. All technical metadata
uses `DM Mono`. This is the privacy-first differentiator — making the data life-cycle of
every message transparent to the user.

**Content rendering rules:**
- Sanitize all HTML with DOMPurify or equivalent before render
- Block `<img>` tags unless user opts in (show count of blocked images)
- Open links in new tab with `rel="noopener noreferrer"`
- Code blocks rendered with `DM Mono` and `canvas-inset` background

---

### 3.5 CommandPalette

Global search and action interface. Keyboard trigger: `⌘K` (macOS) / `Ctrl+K` (Windows/Linux).

#### Layout

```
┌────────────────────────────────────────────────────┐
│  🔍  Search messages, actions, sources…            │  48px input row
├────────────────────────────────────────────────────┤
│  RECENT ACTIONS                                    │  group header (DM Mono 10px)
│    ↩  Mark all read                                │  action row 40px
│    ↩  Archive from GitHub                          │
├────────────────────────────────────────────────────┤
│  MESSAGES                                          │
│    ▶  [Slack] Design review feedback — Anna K.     │  result row 48px
│    ▶  [Email] Q4 Budget approval needed            │
├────────────────────────────────────────────────────┤
│  SOURCES                                           │
│    ⊕  Connect new source…                          │
└────────────────────────────────────────────────────┘
```

#### Interaction Spec

| Trigger | Action |
|---|---|
| `⌘K` / `Ctrl+K` | Open palette, focus input |
| `↑` / `↓` | Navigate results (roving focus) |
| `Enter` | Select highlighted result |
| `Escape` | Close, return focus to previous element |
| Click backdrop | Close |

| Property | Value |
|---|---|
| Backdrop | `ink-950/60` + `backdrop-blur-sm` (8px) |
| Panel bg | `canvas` |
| Panel shadow | `shadow-3` |
| Panel radius | `xl` (16px) |
| Max-width | `560px` |
| Max-height | `480px` (scrollable results) |
| Appear animation | `opacity 0→1` + `scale 0.97→1`, 200ms ease-out |
| Highlighted row bg | `accent-100` |
| Matched text color | `accent-700` |
| Empty state | `ink-400` text, no illustration |

---

### 3.6 SecurityCard

Inline card (popover or Audit Trail section) showing security posture for a message or source.

#### Anatomy

```
┌───────────────────────────────────────────────────┐
│  SECURITY STATUS                                  │
│  ───────────────────────────────────────────────  │
│  ●  Encrypted           E2E · TLS 1.3            │
│  ●  Origin verified     SPF ✓ · DKIM ✓ · DMARC ✓│
│  ○  Tracking pixels     2 blocked                │
│  ○  Read receipt        Not sent                 │
│  ───────────────────────────────────────────────  │
│  Provider: Gmail · Retention: 90 days            │
│  Hash: a3f4…c91d                    [DM Mono]    │
└───────────────────────────────────────────────────┘
```

#### Indicator System

| Symbol | Status | Color | Meaning |
|---|---|---|---|
| `●` filled | Positive/Secure | `secure-500` | Verified, encrypted, safe |
| `○` empty | Neutral | `ink-400` | Informational, not a concern |
| `⚠` triangle | Warning | `warn-500` | Partial or degraded |
| `✗` cross | Negative | `danger-500` | Issue or exposure |

**Accessibility rule:** Never use symbol + color alone. Always include a text label so the
card is legible in grayscale and to screen readers.

---

## 4. Interaction States — Full Reference

### State Matrix

| Component | Default | Hover | Focus-visible | Active/Press | Disabled | Error |
|---|---|---|---|---|---|---|
| InboxItem | `canvas` | `ink-100` bg | focus ring | `accent-50` bg | 40% opacity | `danger-100` bg |
| Button Primary | `accent-700` | `accent-600` | focus ring | `scale-[0.98]` | `ink-200` bg | — |
| Button Ghost | transparent | `ink-100` | focus ring | `ink-200` | `ink-300` text | — |
| Input/Search | `canvas` + `ink-200` border | `ink-300` border | `accent-400` border | — | `canvas` | `danger-500` border |
| SourceBadge | per config | — | — | — | 40% opacity | — |
| PriorityBadge | per config | — | — | — | 40% opacity | — |
| SecurityCard row | per status | `ink-50` bg | focus ring | — | — | — |
| NavItem | transparent | `ink-100` | focus ring | `accent-50` | — | — |
| NavItem (active) | `accent-50` | `accent-100` | focus ring | — | — | — |

### Focus-visible Specification

All interactive elements **must** expose a visible keyboard focus indicator:

```css
/* Light surface */
:focus-visible {
  outline: 2px solid var(--color-accent-400);  /* #7B89D4 */
  outline-offset: 2px;
}

/* Dark surface (e.g. inside modal backdrop) */
.dark-surface :focus-visible {
  box-shadow: 0 0 0 2px #FFFFFF, 0 0 0 4px #7B89D4;
  outline: none;
}
```

**Minimum focus ring size:** 2px width. The offset creates a 4px visible ring from content
edge, meeting WCAG 2.2 Focus Appearance (3:1 against adjacent colors).

### Skeleton / Loading State

Skeleton replaces content during async load. Static in `prefers-reduced-motion`.

```css
@keyframes shimmer {
  0%   { background-position: -400px 0; }
  100% { background-position:  400px 0; }
}

.skeleton {
  background-color: var(--color-ink-100);
  background-image: linear-gradient(
    90deg,
    var(--color-ink-100) 25%,
    var(--color-ink-50)  50%,
    var(--color-ink-100) 75%
  );
  background-size: 800px 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: var(--border-radius-sm);
}

@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
    background-image: none;
  }
}
```

---

## 5. Layout & Responsive Design

### Layout Architecture

#### Desktop (≥ 1024px) — Three-column

```
┌──────────────────────────────────────────────────────────────────────────┐
│ NavRail 240px    │ InboxList 360px      │ ThreadPanel (fluid)            │
│                  │                      │                                │
│ ■ SecureInbox    │ ● Unread (3)         │  [Thread detail content here]  │
│                  │ ──────────────────── │                                │
│  Inbox           │ InboxItem (unread)   │                                │
│  Sent            │ InboxItem (unread)   │                                │
│  Archive         │ InboxItem (read)     │                                │
│  Sources         │ ──────────────────── │                                │
│                  │ InboxItem (read)     │                                │
│ ──────────────── │                      │                                │
│ ⚙ Settings       │                      │                                │
└──────────────────────────────────────────────────────────────────────────┘
```

#### Tablet (768px – 1023px) — Two-column, icon nav

```
┌──────────────────────────────────────────────────┐
│ NavRail 56px   │ InboxList or ThreadPanel         │
│ (icons only)   │ (one panel at a time)            │
│                │                                  │
│ 📥             │ Panel slides horizontally        │
│ 📤             │ (translateX, 300ms ease-out)     │
│ 📂             │                                  │
│ ⊕              │                                  │
└──────────────────────────────────────────────────┘
```

#### Mobile (< 768px) — Full-screen, bottom tabs

```
┌──────────────────────────────────────┐
│ Full-width inbox list                │
│ or thread (full-screen push)         │
│                                      │
│                                      │
│                                      │
├──────────────────────────────────────┤
│  📥 Inbox  📂 Archive  🔍 Search  ⊕  │  56px tab bar
└──────────────────────────────────────┘
```

### Breakpoints

```js
screens: {
  'sm':  '375px',   // mobile baseline
  'md':  '768px',   // tablet breakpoint
  'lg': '1024px',   // desktop breakpoint
  'xl': '1280px',   // wide desktop
}
```

### Panel Behavior

| Panel | Desktop | Tablet | Mobile |
|---|---|---|---|
| NavRail | 240px, always visible | 56px icon-only | Hidden (bottom bar) |
| InboxList | 360px fixed column | Full-width, slides out | Full-screen, slides out |
| ThreadPanel | Fluid (fills rest) | Full-width overlay, slide from right | Full-screen push |

**NavRail collapse (desktop):** `width: 240px → 56px`, `transition: width 200ms ease-out`.
Labels fade out at `opacity 0`, 100ms before width transition completes.

### Empty States

All empty states use `ink-400` text at `text-sm`. No illustrations, no mascots, no
celebratory micro-copy. Calm, direct, functional.

```
No thread selected (desktop):
──────────────────────────────────
          Select a message to read
          or press ⌘K to search
──────────────────────────────────

Inbox is clear:
──────────────────────────────────
          Inbox is clear.
          All messages handled.
──────────────────────────────────

Search returns nothing:
──────────────────────────────────
          No results for "query"
──────────────────────────────────
```

---

## 6. Accessibility (WCAG AA)

### Color & Contrast

- All interactive text: ≥ 4.5 : 1 against background
- Large text (≥ 18px or ≥ 14px bold): ≥ 3 : 1
- Focus indicators: ≥ 3 : 1 against adjacent colors
- Trust-lines: Color + line pattern (redundant encoding for color-blindness)
- Priority badges: Icon + color + text label (never color alone)
- All status indicators (SecurityCard): Symbol + text label

### Keyboard Navigation

| Key | Action |
|---|---|
| `Tab` / `Shift+Tab` | Move between focus groups |
| `↑` / `↓` | Navigate InboxList (roving tabindex) |
| `Enter` / `Space` | Activate focused item |
| `Escape` | Close panel / palette, return focus to trigger |
| `⌘K` / `Ctrl+K` | Open CommandPalette from anywhere |

**Roving tabindex pattern for InboxList:**
- Only the active item has `tabindex="0"`, all others have `tabindex="-1"`
- Arrow keys move active state, not Tab
- Initial focus: first item in list

### ARIA Patterns

```html
<!-- InboxList container -->
<ul role="listbox" aria-label="Inbox messages" aria-multiselectable="false">

  <!-- InboxItem -->
  <li role="option"
      aria-selected="false"
      aria-label="Unread message from Anna K. via Slack, High priority: Design review feedback, received 2 hours ago">
    <!-- visual content; trust-line described via sr-only span -->
    <span class="sr-only">Encryption: End-to-end encrypted</span>
  </li>

</ul>

<!-- ThreadPanel -->
<section role="region" aria-label="Message thread: Design review feedback">

<!-- CommandPalette -->
<div role="dialog" aria-modal="true" aria-label="Command palette">
  <input role="combobox"
         aria-expanded="true"
         aria-haspopup="listbox"
         aria-controls="cmd-results"
         aria-autocomplete="list" />
  <ul role="listbox" id="cmd-results">
    <li role="option" aria-selected="true">Mark all read</li>
  </ul>
</div>

<!-- SourceBadge -->
<span role="img" aria-label="Source: Slack">◆ Slack</span>

<!-- Unread count live region -->
<span aria-live="polite" aria-atomic="true" class="sr-only">
  3 unread messages
</span>
```

### Focus Management

| Scenario | Focus behavior |
|---|---|
| CommandPalette opens | Moves to search input |
| CommandPalette closes | Returns to `⌘K` trigger element |
| Thread opens (mobile) | Moves to thread header back button |
| Thread closes | Returns to InboxItem that opened it |
| Error toast appears | `aria-live="assertive"` (errors only) |

### Touch Targets

All interactive elements meet minimum touch target on mobile:

| Element | Min size |
|---|---|
| InboxItem | 64px height |
| Bottom tab item | 56px height, full-width zone |
| Buttons | 44×44px minimum |
| Attachment pill | 44px height |
| NavRail icon (tablet) | 44×44px |

---

## 7. React + Tailwind Snippets

### 7.0 Setup

**tailwind.config.ts**

```ts
import type { Config } from 'tailwindcss'

export default {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        ui:   ['DM Sans',  'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['DM Mono',  'Cascadia Code', 'monospace'],
      },
      colors: {
        canvas: {
          DEFAULT: '#FFFFFF',
          subtle:  '#F4F6F8',
          inset:   '#ECEEF2',
        },
        ink: {
          950: '#0D1117',
          800: '#1E2432',
          600: '#4A5568',
          400: '#8896A8',
          300: '#A0AABB',
          200: '#C5CED8',
          100: '#E4E8EE',
          50:  '#F4F6F8',
        },
        accent: {
          800: '#1E2A7A',
          700: '#2D3A8C',
          600: '#3B4BA3',
          400: '#7B89D4',
          100: '#EEF0FB',
          50:  '#F5F6FD',
        },
        secure: {
          700: '#0F5E4D',
          500: '#1A8A70',
          300: '#5CB89B',
          100: '#E4F5F0',
          50:  '#F0FAF7',
        },
        warn: {
          700: '#9A4E0A',
          500: '#C2600A',
          100: '#FDF0E6',
        },
        danger: {
          700: '#9B1C1C',
          500: '#C42B2B',
          100: '#FDF0F0',
        },
        source: {
          email:  '#2D3A8C',
          slack:  '#4A1C6B',
          github: '#1A2332',
          linear: '#1A3B5C',
          other:  '#3D4458',
        },
      },
      borderRadius: {
        sm: '3px',
        md: '6px',
        lg: '10px',
        xl: '16px',
      },
      boxShadow: {
        '1':     '0 1px 3px 0 rgba(14,18,27,0.06), 0 1px 2px -1px rgba(14,18,27,0.04)',
        '2':     '0 4px 12px 0 rgba(14,18,27,0.10), 0 2px 4px -1px rgba(14,18,27,0.06), 0 0 0 1px rgba(14,18,27,0.04)',
        '3':     '0 16px 48px -8px rgba(14,18,27,0.18), 0 4px 16px -4px rgba(14,18,27,0.10), 0 0 0 1px rgba(14,18,27,0.06)',
        'focus': '0 0 0 2px #FFFFFF, 0 0 0 4px #7B89D4',
      },
      animation: {
        'shimmer':        'shimmer 1.5s ease-in-out infinite',
        'priority-pulse': 'priority-pulse 2s ease-in-out infinite',
        'fade-in-scale':  'fadeInScale 200ms cubic-bezier(0.16,1,0.3,1)',
      },
      keyframes: {
        shimmer: {
          '0%':   { backgroundPosition: '-400px 0' },
          '100%': { backgroundPosition:  '400px 0' },
        },
        'priority-pulse': {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.4' },
        },
        fadeInScale: {
          from: { opacity: '0', transform: 'translateX(-50%) scale(0.97)' },
          to:   { opacity: '1', transform: 'translateX(-50%) scale(1)' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config
```

**src/lib/utils.ts**

```ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

---

### 7.1 SourceBadge

```tsx
// src/components/ui/SourceBadge.tsx
import { cn } from '@/lib/utils'

export type Source = 'email' | 'slack' | 'github' | 'linear' | 'other'

const SOURCE_CONFIG: Record<
  Source,
  { label: string; icon: string; colorClass: string }
> = {
  email:  { label: 'Email',  icon: '✉', colorClass: 'text-source-email  bg-source-email/10'  },
  slack:  { label: 'Slack',  icon: '◆', colorClass: 'text-source-slack  bg-source-slack/10'  },
  github: { label: 'GitHub', icon: '◎', colorClass: 'text-source-github bg-source-github/10' },
  linear: { label: 'Linear', icon: '■', colorClass: 'text-source-linear bg-source-linear/10' },
  other:  { label: 'Other',  icon: '●', colorClass: 'text-source-other  bg-source-other/10'  },
}

interface SourceBadgeProps {
  source: Source
  className?: string
}

export function SourceBadge({ source, className }: SourceBadgeProps) {
  const { label, icon, colorClass } = SOURCE_CONFIG[source]

  return (
    <span
      role="img"
      aria-label={`Source: ${label}`}
      className={cn(
        'inline-flex items-center gap-1',
        'px-1.5 py-0.5',
        'rounded-sm',
        'text-[11px] font-medium font-ui leading-none tracking-[0.02em]',
        colorClass,
        className
      )}
    >
      <span aria-hidden="true" className="text-[10px]">{icon}</span>
      <span className="max-w-[56px] truncate">{label}</span>
    </span>
  )
}
```

---

### 7.2 PriorityBadge

```tsx
// src/components/ui/PriorityBadge.tsx
import { cn } from '@/lib/utils'

export type Priority = 'critical' | 'high' | 'normal' | 'low'

interface PriorityBadgeProps {
  priority: Priority
  className?: string
}

const PRIORITY_CONFIG = {
  critical: {
    label: 'CRITICAL',
    icon: '◉',
    classes: 'text-danger-700 bg-danger-100',
    iconClass: 'animate-priority-pulse motion-reduce:animate-none',
  },
  high: {
    label: 'HIGH',
    icon: '▲',
    classes: 'text-warn-700 bg-warn-100',
    iconClass: '',
  },
  normal: null,   // no badge rendered — absence conveys Normal
  low: {
    label: 'LOW',
    icon: '▽',
    classes: 'text-ink-400 bg-ink-100',
    iconClass: '',
  },
} as const

export function PriorityBadge({ priority, className }: PriorityBadgeProps) {
  const config = PRIORITY_CONFIG[priority]
  if (!config) return null

  return (
    <span
      aria-label={`Priority: ${config.label}`}
      className={cn(
        'inline-flex items-center gap-1',
        'px-1.5 py-0.5',
        'rounded-sm',
        'text-[11px] font-semibold font-ui leading-none tracking-[0.04em]',
        config.classes,
        className
      )}
    >
      <span aria-hidden="true" className={cn('text-[10px]', config.iconClass)}>
        {config.icon}
      </span>
      <span>{config.label}</span>
    </span>
  )
}
```

---

### 7.3 InboxItem

```tsx
// src/components/InboxItem.tsx
import { cn } from '@/lib/utils'
import { SourceBadge, type Source } from '@/components/ui/SourceBadge'
import { PriorityBadge, type Priority } from '@/components/ui/PriorityBadge'

export type TrustLevel = 'encrypted' | 'partial' | 'unknown'

interface InboxItemProps {
  id: string
  sender: string
  subject: string
  preview: string
  time: string
  source: Source
  priority?: Priority
  trust: TrustLevel
  isRead?: boolean
  isSelected?: boolean
  isDisabled?: boolean
  hasError?: boolean
  onClick?: () => void
}

const TRUST_STYLE: Record<
  TrustLevel,
  { borderColor: string; borderStyle: string; srLabel: string }
> = {
  encrypted: {
    borderColor: 'border-secure-500',
    borderStyle: 'border-solid',
    srLabel: 'End-to-end encrypted',
  },
  partial: {
    borderColor: 'border-warn-500',
    borderStyle: 'border-dashed',
    srLabel: 'Partial encryption — in transit',
  },
  unknown: {
    borderColor: 'border-ink-300',
    borderStyle: 'border-dotted',
    srLabel: 'Encryption status unknown',
  },
}

export function InboxItem({
  sender,
  subject,
  preview,
  time,
  source,
  priority = 'normal',
  trust,
  isRead = false,
  isSelected = false,
  isDisabled = false,
  hasError = false,
  onClick,
}: InboxItemProps) {
  const trustStyle = TRUST_STYLE[trust]
  const initial = sender.charAt(0).toUpperCase()

  return (
    <li
      role="option"
      aria-selected={isSelected}
      aria-disabled={isDisabled}
      aria-label={[
        isRead ? '' : 'Unread.',
        `From ${sender} via ${source}.`,
        priority !== 'normal' ? `Priority: ${priority}.` : '',
        subject,
      ].filter(Boolean).join(' ')}
    >
      <button
        disabled={isDisabled}
        onClick={onClick}
        className={cn(
          // Layout
          'w-full flex items-start gap-3 px-4 py-3 text-left',
          // Trust-line (left border)
          'border-l-2',
          trustStyle.borderColor,
          trustStyle.borderStyle,
          // Background states
          !isSelected && !hasError && 'bg-canvas hover:bg-ink-100',
          isSelected                 && 'bg-accent-50',
          hasError                   && 'bg-danger-100',
          // Transition
          'transition-colors duration-150 ease-out',
          // Focus
          'focus-visible:outline-none focus-visible:shadow-focus',
          // Disabled
          isDisabled && 'opacity-40 cursor-not-allowed pointer-events-none',
        )}
      >
        {/* Avatar — initials only, no remote fetch */}
        <div
          aria-hidden="true"
          className={cn(
            'flex-shrink-0 w-8 h-8 rounded-full',
            'flex items-center justify-center mt-0.5',
            'bg-ink-100 text-ink-600',
            'text-sm font-semibold font-ui select-none',
          )}
        >
          {initial}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">

          {/* Row 1: sender · badges · time */}
          <div className="flex items-center gap-1.5 mb-0.5">
            <span
              className={cn(
                'text-sm font-ui flex-1 min-w-0 truncate',
                isRead ? 'font-normal text-ink-600' : 'font-semibold text-ink-950',
              )}
            >
              {sender}
            </span>
            <div className="flex items-center gap-1 flex-shrink-0">
              <SourceBadge source={source} />
              {priority !== 'normal' && <PriorityBadge priority={priority} />}
              <span className="text-[11px] font-mono text-ink-400 tabular-nums ml-0.5">
                {time}
              </span>
            </div>
          </div>

          {/* Row 2: subject */}
          <p
            className={cn(
              'text-sm font-ui truncate mb-0.5',
              isRead ? 'text-ink-600 font-normal' : 'text-ink-800 font-medium',
            )}
          >
            {subject}
          </p>

          {/* Row 3: preview */}
          <p className={cn('text-xs font-ui truncate', isRead ? 'text-ink-400' : 'text-ink-600')}>
            {preview}
          </p>

        </div>

        {/* Unread indicator dot */}
        {!isRead && (
          <div
            aria-hidden="true"
            className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-accent-700 mt-2"
          />
        )}

        {/* Screen-reader trust description */}
        <span className="sr-only">Encryption: {trustStyle.srLabel}</span>
      </button>
    </li>
  )
}
```

---

### 7.4 SkeletonInboxItem

```tsx
// src/components/ui/SkeletonInboxItem.tsx
import { cn } from '@/lib/utils'

function Bone({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      style={{
        backgroundImage:
          'linear-gradient(90deg, #E4E8EE 25%, #F4F6F8 50%, #E4E8EE 75%)',
        backgroundSize: '800px 100%',
      }}
      className={cn(
        'rounded-sm bg-ink-100',
        'animate-shimmer motion-reduce:animate-none motion-reduce:bg-ink-100',
        className
      )}
    />
  )
}

export function SkeletonInboxItem() {
  return (
    <li
      aria-busy="true"
      aria-label="Loading message"
      className="flex items-start gap-3 px-4 py-3 border-l-2 border-ink-200 border-solid"
    >
      {/* Avatar */}
      <Bone className="w-8 h-8 rounded-full flex-shrink-0 mt-0.5" />

      {/* Lines */}
      <div className="flex-1 min-w-0 space-y-1.5 pt-0.5">
        <div className="flex items-center gap-2">
          <Bone className="h-3 w-28 rounded-sm" />
          <Bone className="h-3 w-10 ml-auto rounded-sm" />
        </div>
        <Bone className="h-3 w-3/4 rounded-sm" />
        <Bone className="h-2.5 w-1/2 rounded-sm" />
      </div>
    </li>
  )
}
```

---

### 7.5 SecurityCard

```tsx
// src/components/SecurityCard.tsx
import { cn } from '@/lib/utils'

export type IndicatorStatus = 'positive' | 'neutral' | 'warning' | 'negative'

export interface SecurityRow {
  status: IndicatorStatus
  label: string
  detail: string
}

interface SecurityCardProps {
  rows: SecurityRow[]
  provider?: string
  retention?: string
  hash?: string
  className?: string
}

const INDICATOR: Record<
  IndicatorStatus,
  { symbol: string; colorClass: string; ariaLabel: string }
> = {
  positive: { symbol: '●', colorClass: 'text-secure-500', ariaLabel: 'Secure'        },
  neutral:  { symbol: '○', colorClass: 'text-ink-400',    ariaLabel: 'Informational' },
  warning:  { symbol: '⚠', colorClass: 'text-warn-500',   ariaLabel: 'Warning'       },
  negative: { symbol: '✗', colorClass: 'text-danger-500', ariaLabel: 'Issue'         },
}

export function SecurityCard({
  rows,
  provider,
  retention,
  hash,
  className,
}: SecurityCardProps) {
  return (
    <div
      role="region"
      aria-label="Security status"
      className={cn(
        'rounded-md border border-ink-200 bg-canvas shadow-1',
        'p-4 font-ui',
        className,
      )}
    >
      {/* Header */}
      <h3 className="text-[10px] font-mono font-semibold text-ink-400 tracking-[0.08em] uppercase mb-3">
        Security Status
      </h3>

      {/* Rows */}
      <ul className="space-y-1">
        {rows.map((row, i) => {
          const ind = INDICATOR[row.status]
          return (
            <li
              key={i}
              className="flex items-start gap-2 -mx-2 px-2 py-1 rounded-sm hover:bg-ink-50 transition-colors"
            >
              <span
                aria-label={ind.ariaLabel}
                className={cn('text-xs mt-px flex-shrink-0', ind.colorClass)}
              >
                {ind.symbol}
              </span>
              <span className="flex-1 text-xs text-ink-800">{row.label}</span>
              <span className="text-xs font-mono text-ink-500 flex-shrink-0 text-right">
                {row.detail}
              </span>
            </li>
          )
        })}
      </ul>

      {/* Footer metadata */}
      {(provider || retention || hash) && (
        <div className="mt-3 pt-3 border-t border-ink-100 space-y-1">
          {provider && (
            <p className="text-xs text-ink-400">
              Provider:{' '}
              <span className="text-ink-600">{provider}</span>
            </p>
          )}
          {retention && (
            <p className="text-xs text-ink-400">
              Retention:{' '}
              <span className="text-ink-600">{retention}</span>
            </p>
          )}
          {hash && (
            <p className="text-xs text-ink-400">
              Hash:{' '}
              <span className="font-mono text-ink-500 tracking-tight">{hash}</span>
            </p>
          )}
        </div>
      )}
    </div>
  )
}

/*
 * Usage:
 *
 * <SecurityCard
 *   rows={[
 *     { status: 'positive', label: 'Encrypted',       detail: 'E2E · TLS 1.3'     },
 *     { status: 'positive', label: 'Origin verified', detail: 'SPF ✓ DKIM ✓'      },
 *     { status: 'neutral',  label: 'Tracking pixels', detail: '2 blocked'          },
 *     { status: 'neutral',  label: 'Read receipt',    detail: 'Not sent'           },
 *   ]}
 *   provider="Gmail"
 *   retention="90 days"
 *   hash="a3f4…c91d"
 * />
 */
```

---

### 7.6 CommandPalette

```tsx
// src/components/CommandPalette.tsx
import { useState, useEffect, useRef, useCallback } from 'react'
import { cn } from '@/lib/utils'

export interface CommandItem {
  id: string
  group: 'actions' | 'messages' | 'sources'
  label: string
  sublabel?: string
  icon?: string
  onSelect: () => void
}

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  items: CommandItem[]
}

const GROUP_LABELS: Record<CommandItem['group'], string> = {
  actions:  'RECENT ACTIONS',
  messages: 'MESSAGES',
  sources:  'SOURCES',
}

export function CommandPalette({ isOpen, onClose, items }: CommandPaletteProps) {
  const [query, setQuery]     = useState('')
  const [activeIdx, setActive] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const filtered = query.trim()
    ? items.filter(i =>
        i.label.toLowerCase().includes(query.toLowerCase()) ||
        i.sublabel?.toLowerCase().includes(query.toLowerCase())
      )
    : items

  // Reset and focus on open
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setActive(0)
      // rAF ensures the DOM is painted before we focus
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [isOpen])

  const handleKey = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setActive(i => Math.min(i + 1, filtered.length - 1))
          break
        case 'ArrowUp':
          e.preventDefault()
          setActive(i => Math.max(i - 1, 0))
          break
        case 'Enter':
          e.preventDefault()
          filtered[activeIdx]?.onSelect()
          onClose()
          break
        case 'Escape':
          onClose()
          break
      }
    },
    [filtered, activeIdx, onClose],
  )

  if (!isOpen) return null

  const groups = (['actions', 'messages', 'sources'] as const)
    .map(g => ({ group: g, items: filtered.filter(i => i.group === g) }))
    .filter(g => g.items.length > 0)

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        className="fixed inset-0 z-40 bg-ink-950/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        className={cn(
          'fixed z-50 top-[18%] left-1/2',
          'w-[calc(100%-2rem)] max-w-[560px]',
          'bg-canvas rounded-xl shadow-3',
          'animate-fade-in-scale motion-reduce:animate-none',
        )}
        onKeyDown={handleKey}
      >
        {/* Search input row */}
        <div className="flex items-center gap-3 px-4 h-12 border-b border-ink-100">
          <span aria-hidden="true" className="text-ink-400 text-sm flex-shrink-0">🔍</span>
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded="true"
            aria-haspopup="listbox"
            aria-controls="cmd-results"
            aria-autocomplete="list"
            value={query}
            onChange={e => { setQuery(e.target.value); setActive(0) }}
            placeholder="Search messages, actions, sources…"
            className={cn(
              'flex-1 bg-transparent',
              'text-sm font-ui text-ink-800 placeholder:text-ink-400',
              'outline-none',
            )}
          />
          <kbd className="text-[10px] font-mono text-ink-300 border border-ink-200 rounded-sm px-1.5 py-0.5 flex-shrink-0">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <ul
          id="cmd-results"
          role="listbox"
          aria-label="Search results"
          className="max-h-[400px] overflow-y-auto py-2"
        >
          {groups.length === 0 && (
            <li className="px-4 py-8 text-center text-sm text-ink-400 font-ui">
              No results for "{query}"
            </li>
          )}

          {groups.map(({ group, items: gItems }) => (
            <li key={group}>
              {/* Group header */}
              <p className="px-4 pt-2 pb-1 text-[10px] font-mono font-semibold text-ink-400 tracking-[0.08em]">
                {GROUP_LABELS[group]}
              </p>

              <ul>
                {gItems.map(item => {
                  const globalIdx = filtered.indexOf(item)
                  const isActive  = globalIdx === activeIdx

                  return (
                    <li key={item.id} role="option" aria-selected={isActive}>
                      <button
                        className={cn(
                          'w-full flex items-center gap-3 px-4 py-2.5 text-left',
                          'text-sm font-ui',
                          'transition-colors duration-75',
                          isActive
                            ? 'bg-accent-100 text-accent-700'
                            : 'text-ink-800 hover:bg-ink-50',
                        )}
                        onClick={() => { item.onSelect(); onClose() }}
                        onMouseEnter={() => setActive(globalIdx)}
                      >
                        {item.icon && (
                          <span
                            aria-hidden="true"
                            className="w-4 text-center flex-shrink-0 text-ink-400 text-xs"
                          >
                            {item.icon}
                          </span>
                        )}
                        <span className="flex-1 truncate">{item.label}</span>
                        {item.sublabel && (
                          <span className="text-xs text-ink-400 truncate max-w-[160px]">
                            {item.sublabel}
                          </span>
                        )}
                      </button>
                    </li>
                  )
                })}
              </ul>
            </li>
          ))}
        </ul>
      </div>
    </>
  )
}
```

---

### 7.7 ThreadPanel (shell)

```tsx
// src/components/ThreadPanel.tsx
import { useState } from 'react'
import { cn } from '@/lib/utils'
import { SecurityCard } from './SecurityCard'

interface Attachment {
  name: string
  size: string
}

interface ThreadMessage {
  id: string
  sender: string
  senderEmail: string
  time: string
  subject: string
  bodyHtml: string          // pre-sanitized (DOMPurify)
  hasExternalImages?: boolean
  attachments?: Attachment[]
}

interface ThreadPanelProps {
  message: ThreadMessage | null
  onBack?: () => void
  className?: string
}

export function ThreadPanel({ message, onBack, className }: ThreadPanelProps) {
  const [showImages, setShowImages] = useState(false)
  const [auditOpen, setAuditOpen]   = useState(false)

  /* ── Empty state ──────────────────────────────────────── */
  if (!message) {
    return (
      <div
        role="region"
        aria-label="Message detail"
        className={cn('flex flex-col items-center justify-center h-full bg-canvas-subtle', className)}
      >
        <p className="text-sm font-ui text-ink-400 text-center">
          Select a message to read
          <br />
          <span className="text-xs text-ink-300 block mt-1">or press ⌘K to search</span>
        </p>
      </div>
    )
  }

  /* ── Thread detail ────────────────────────────────────── */
  return (
    <section
      role="region"
      aria-label={`Message thread: ${message.subject}`}
      className={cn('flex flex-col h-full bg-canvas', className)}
    >
      {/* Header */}
      <header className="flex items-center gap-2 px-6 py-4 border-b border-ink-100 flex-shrink-0">
        {onBack && (
          <button
            onClick={onBack}
            aria-label="Back to inbox"
            className={cn(
              'lg:hidden p-1.5 rounded-md',
              'text-ink-400 hover:bg-ink-100 hover:text-ink-800',
              'focus-visible:outline-none focus-visible:shadow-focus',
              'transition-colors',
            )}
          >
            ←
          </button>
        )}
        <div className="flex-1" />
        <button
          aria-label="Message options"
          className={cn(
            'p-1.5 rounded-md',
            'text-ink-400 hover:bg-ink-100',
            'focus-visible:outline-none focus-visible:shadow-focus',
            'transition-colors',
          )}
        >
          ⋯
        </button>
      </header>

      {/* Message meta */}
      <div className="px-6 pt-5 pb-4 border-b border-ink-100 flex-shrink-0">
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-sm font-semibold font-ui text-ink-800 flex-1 truncate">
            {message.sender}
          </span>
          <span className="text-xs font-mono text-ink-400 flex-shrink-0 tabular-nums">
            {message.time}
          </span>
        </div>
        <p className="text-xs font-mono text-ink-400 mb-4">
          To: <span className="text-ink-600">{message.senderEmail}</span>
        </p>
        <h1 className="text-xl font-semibold font-ui text-ink-950 leading-snug tracking-tight">
          {message.subject}
        </h1>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-6 py-5">

        {/* External images blocked banner */}
        {message.hasExternalImages && !showImages && (
          <div className="mb-4 flex items-center gap-3 px-3 py-2.5 rounded-md bg-warn-100 border border-warn-500/20">
            <p className="text-xs font-ui text-warn-700 flex-1">
              External images blocked to protect your privacy.
            </p>
            <button
              onClick={() => setShowImages(true)}
              className={cn(
                'text-xs font-semibold text-warn-700 hover:underline',
                'focus-visible:outline-none focus-visible:shadow-focus rounded',
              )}
            >
              Show images
            </button>
          </div>
        )}

        {/* Message body — consumer must sanitize before passing bodyHtml */}
        <div
          className="prose prose-sm max-w-none text-ink-800 font-ui"
          dangerouslySetInnerHTML={{ __html: message.bodyHtml }}
        />

        {/* Attachments */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="mt-6 flex flex-wrap gap-2" aria-label="Attachments">
            {message.attachments.map(att => (
              <button
                key={att.name}
                aria-label={`Download attachment: ${att.name}, ${att.size}`}
                className={cn(
                  'flex items-center gap-2 px-3 py-2',
                  'rounded-md border border-ink-200 bg-canvas-subtle',
                  'hover:bg-ink-100',
                  'transition-colors text-xs font-ui',
                  'focus-visible:outline-none focus-visible:shadow-focus',
                )}
              >
                <span aria-hidden="true" className="text-ink-400">📎</span>
                <span className="text-ink-800 font-medium">{att.name}</span>
                <span className="font-mono text-ink-400">{att.size}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Privacy Audit Trail — collapsed by default */}
      <div className="border-t border-ink-100 flex-shrink-0">
        <button
          onClick={() => setAuditOpen(o => !o)}
          aria-expanded={auditOpen}
          aria-controls="privacy-audit-trail"
          className={cn(
            'w-full flex items-center justify-between px-6 py-3',
            'text-[10px] font-mono font-semibold text-ink-400 tracking-[0.08em] uppercase',
            'hover:bg-ink-50 transition-colors',
            'focus-visible:outline-none focus-visible:shadow-focus',
          )}
        >
          <span>Privacy Audit Trail</span>
          <span
            aria-hidden="true"
            className={cn('transition-transform duration-150', auditOpen && 'rotate-180')}
          >
            ↕
          </span>
        </button>

        {auditOpen && (
          <div id="privacy-audit-trail" className="px-4 pb-4">
            <SecurityCard
              rows={[
                { status: 'positive', label: 'Encrypted',        detail: 'E2E · TLS 1.3'  },
                { status: 'positive', label: 'Origin verified',  detail: 'SPF ✓ DKIM ✓'   },
                { status: 'neutral',  label: 'Tracking pixels',  detail: '2 blocked'       },
                { status: 'neutral',  label: 'Read receipt',     detail: 'Not sent'        },
              ]}
              provider="Gmail"
              retention="90 days"
              hash="a3f4…c91d"
            />
          </div>
        )}
      </div>
    </section>
  )
}
```

---

## 8. Global CSS (globals.css)

```css
/* Import typefaces */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:ital,wght@0,400;0,500;1,400&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

/* ── Base resets ───────────────────────────────────── */
*, *::before, *::after {
  box-sizing: border-box;
}

html {
  font-family: var(--font-ui, 'DM Sans', ui-sans-serif, sans-serif);
  background-color: #F4F6F8;
  color: #1E2432;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ── Focus ring ────────────────────────────────────── */
:focus-visible {
  outline: 2px solid #7B89D4;
  outline-offset: 2px;
}

/* ── Reduced motion ────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration:        0.01ms !important;
    animation-iteration-count: 1      !important;
    transition-duration:       0.01ms !important;
    scroll-behavior:           auto   !important;
  }
}

/* ── Screen reader only ────────────────────────────── */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
```

---

## 9. Design Decision Log

| Decision | Rationale |
|---|---|
| `DM Sans` over Inter | Avoided the most overused typeface in SaaS. DM Sans carries a slightly mechanical quality appropriate for a security tool, with better optical balance at 13–15px |
| Slate-indigo accent (`#2D3A8C`) | Standard bright blue reads as "generic SaaS." Slate-indigo reads as "institutional, deliberate" — closer to a Bloomberg terminal than a todo app |
| Cool-neutral page base (`#F4F6F8`) | Warm backgrounds signal personal and editorial. Cool gray signals institutional trust and focus |
| Trust-lines via border-style + color | Color-blind accessible: dashed and dotted patterns convey the same information without relying on hue alone |
| No priority badge for Normal | Absence of information is information. Reduces visual noise for the default case (≈ 90% of messages) |
| Privacy Audit Trail collapsed | Shows the feature exists without interrupting reading. Users who care can open it; users who don't, won't |
| Avatars as initials only | Prevents silent email-address-to-avatar API calls. No remote asset fetches without opt-in |
| External images blocked by default | Tracking pixels and remote images are both a privacy risk and a security risk |
| No celebratory empty states | A security product's empty inbox is calm, not celebrated. No mascots, no confetti |
| `DM Mono` for all metadata | Creates a clear visual layer: humanistic UI = DM Sans; machine-generated metadata = DM Mono |
| Shadow-3 for CommandPalette only | High-elevation shadows draw focus to the most important floating surface. Using them everywhere dilutes the signal |

---

*SecureInbox Design Spec v1.0 · June 2026*
