# ALLinO Sprint 5 Release Hardening Checklist

Date: 2026-07-01
Scope: post-S5 verification snapshot.

## 1) Wave 2 Readiness Coverage

- [x] Discord connector implemented (`/connectors/discord/sync`) with mapping and endpoint tests.
- [x] Capabilities matrix includes Wave 2 flags for `discord`, `zoom`, `teams`.
- [x] Zoom/Teams are represented as not yet available for sync while still exposing runtime `configured` readiness.

## 2) Runtime Configuration Signals

- [x] `configured` is derived from runtime env vars for all listed connectors.
- [x] Secret-dependent connectors keep `requires_secret=true` semantics.
- [x] `.env.example` includes Wave 2 token placeholders for operational setup.

## 3) Frontend Operational UX

- [x] Sources panel displays explicit setup indicator when `configured=false`.
- [x] Dynamic source list remains capability-driven (no hardcoded registry list).
- [x] Existing connector telemetry/runs rendering remains intact after indicator update.

## 4) Smoke and Validation Evidence

- [x] Smoke runbook extended with Slack seeded sync scenario.
- [x] Smoke runbook extended with Discord seeded sync scenario.
- [x] Backend suite passes after Sprint 5 updates (`pytest -q` => 85 passed).
- [x] Frontend build passes after Sources indicator update (`npm --prefix frontend run build` => success).

## 5) Go / No-Go

Current assessment: GO for continued Sprint delivery baseline.

Before production cut:

1. Execute Slack + Discord smoke scenarios against staging secrets.
2. Validate capability readiness flags in staging env matrix (dev/stage/prod).
3. Keep Zoom/Teams entries flagged unavailable until connector endpoints are implemented and tested.
