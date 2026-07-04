# ALLinO Sprint 4 Release Hardening Checklist

Date: 2026-07-01
Scope: post-S4-04 verification snapshot.

## 1) Integration Coverage

- [x] Slack connector implemented (`/connectors/slack/sync`) with mapping and endpoint tests.
- [x] Jira + Telegram remain green from Sprint 3.
- [x] Capabilities matrix includes all active sources (`github`, `gitlab`, `jira`, `linear`, `telegram`, `slack`).

## 2) Runtime Configuration

- [x] Capabilities endpoint reflects runtime env configuration (`configured` flags).
- [x] Secret-dependent connectors marked with `requires_secret=true`.
- [x] Slack configuration requires both token and channel id.

## 3) Event Bus and Read Path

- [x] Event-bus Redis mode documented in smoke runbook.
- [x] Fallback behavior documented for unavailable Redis.
- [x] Frontend inbox polling moved to cursor-based `/inbox/page` path.

## 4) Quality Gates

- [x] Backend test suite passes after Sprint 4 updates (`pytest -q` => 82 passed).
- [x] Frontend build passes after inbox polling migration (`npm --prefix frontend run build` => success).
- [x] CI hardening from Sprint 3 still active (matrix + artifact uploads).

## 5) Go / No-Go

Current assessment: GO for continued delivery baseline.

Before production cut:

1. Run Redis-enabled smoke path in target deployment environment.
2. Validate connector secrets provisioning per environment.
3. Freeze Sprint 4 board and handoff docs after final smoke evidence capture.
