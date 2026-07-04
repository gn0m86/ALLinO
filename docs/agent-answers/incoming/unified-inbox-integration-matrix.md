# Unified Inbox — Integration Matrix

> Solution Architecture · 13 services · Wave prioritization

---

## Legend

| Symbol | Meaning |
|--------|---------|
| 🔵 Wave 1 | First release — high priority |
| 🟣 Wave 2 | Second iteration |
| 🟢 Wave 3 | Future / low priority |
| ⚠️ | Privileged scope / special approval required |

---

## Full Integration Matrix

| # | Service | Events | Retrieval model | Scopes / Permissions | Rate limits / Quotas | Complexity | Security / Compliance | Wave |
|---|---------|--------|-----------------|----------------------|----------------------|------------|-----------------------|------|
| 1 | **Slack** | DMs, @mentions, app mentions, channel msgs, reactions, thread replies | Webhook (Events API) + WebSocket (Socket Mode) | `channels:history` `im:history` `groups:history` `app_mentions:read` `users:read` `reactions:read` | Tier 1: 1 req/min · Tier 4: 100+ req/min · Socket Mode: real-time · Web API: per-method | 🟡 Med | 🟡 Med — SOC2 T2 ✓, GDPR ✓. Risk: DM data exposure, workspace-wide scopes | 🔵 Wave 1 |
| 2 | **GitHub** | PR comments, issue mentions, review requests, CI/CD alerts, release events, workflow runs | Webhook | `repo` `notifications` `issues` `pull_requests` · Fine-grained PAT ✓ | 5,000 req/hr (auth) · 60 req/hr (anon) · Secondary limits apply · Webhook: real-time | 🟢 Low | 🟢 Low — SOC2 T2 ✓. Fine-grained tokens ✓. Code content not exposed. Lowest risk in list | 🔵 Wave 1 |
| 3 | **GitLab** | MR comments, issue mentions, pipeline events, CI/CD notif., notes/threads | Webhook + REST polling | `read_api` `read_user` `read_repository` | GitLab.com: 2,000/min · Self-hosted: configurable · Webhook: real-time · Pipeline events: unlimited | 🟢 Low | 🔵 Low–Med — SOC2 T2 (cloud) ✓. Self-hosted: TLS/auth not guaranteed | 🔵 Wave 1 |
| 4 | **Jira** | Issue created/updated, comments, assignments, status transitions, sprint events, epic changes | Webhook (Cloud) + REST polling (Server/DC) | `read:jira-work` `read:jira-user` `manage:jira-webhook` | Cloud: ~10,000 req/hr · Max 50 webhooks/project · Server/DC: no limit · Retry policy required | 🟡 Med | 🟡 Med — SOC2, ISO27001 ✓. Server: HTTPS optional. Project data is sensitive | 🔵 Wave 1 |
| 5 | **Google Calendar / Meet** | Event created/updated, event cancelled, RSVP changes, Meet link gen., recurring events | Push (watch API) + REST polling | `calendar.readonly` `calendar.events.readonly` | 1M queries/day · 500 req/100s per user · **Watch TTL: 7 days — renewal cron required!** | 🟡 Med | 🟢 Low — SOC 1/2/3, ISO27001 ✓, GDPR ✓. Watch channels expire silently | 🔵 Wave 1 |
| 6 | **Discord** | DMs, guild messages, mentions, thread msgs, reactions, voice events | WebSocket (Gateway) + Webhook (outgoing) | ⚠️ `MESSAGE_CONTENT` (privileged) `GUILDS` `GUILD_MESSAGES` `DIRECT_MESSAGES` | 50 req/s (global) · 5 req/5s per route · Gateway: 120 events/min · Privileged intent: verify >100 servers | 🟡 Med | 🟡 Med — MESSAGE_CONTENT is privileged. >100 servers requires verification. Not GDPR-certified. Discord ToS restrictions | 🟣 Wave 2 |
| 7 | **Linear** | Issues created/updated, comments, cycle changes, project updates, assignments, priority changes | Webhook + GraphQL subscriptions | `read` (OAuth 2.0) · `issues:create` | 1,500 req/hr (GraphQL) · 400 complexity pts/query · Webhook: real-time · Best limits in the list | 🟢 Low | 🟢 Low — SOC2 T2 ✓. Modern OAuth2 ✓. Minimal PII exposure. Excellent docs | 🟣 Wave 2 |
| 8 | **MS Teams** | DMs, channel mentions, meeting notif., adaptive cards, presence changes | Bot Framework + Graph API webhooks | `Chat.Read` `ChannelMessage.Read.All` `Presence.Read.All` `Calendars.Read` | 4 req/s per app/tenant · 3,000 req/10s per app · Bot: 1,800 msg/min/app · Graph: per-resource throttle | 🔴 High | 🟢 Low — SOC1/2, ISO27001 ✓, HIPAA, FedRAMP ✓. Requires Azure AD app + Bot Framework setup | 🟣 Wave 2 |
| 9 | **Zoom** | Meeting start/end, participant join/leave, recording ready, webinar events, cloud recording | Webhook (Event Subscriptions) | `meeting:read:admin` `webinar:read:admin` `recording:read` | 100 req/s (global) · Some endpoints: 1 req/s · Recording: 1 req/s · Max 30 subscriptions/app | 🟢 Low | 🟡 Med — SOC2 T2 ✓. HIPAA addon available. Risk: recording data access. Limited audit trail | 🟣 Wave 2 |
| 10 | **Telegram** | Bot DMs, group mentions, commands, file shares, inline queries, poll results | Webhook + Long polling (getUpdates) | Bot Token (no OAuth) · Group admin rights | 30 msg/s (global) · 20 msg/min per chat · getUpdates: 100 req/s · Files: up to 50MB | 🟢 Low | 🟡 Med — No E2E in groups. UAE jurisdiction. GDPR: gray area. Not enterprise-certified | 🟣 Wave 2 |
| 11 | **Rocket.Chat** | DMs, channel messages, mentions, room notif., file shares, integration events | WebSocket (Realtime API) + Webhook + REST API | `API Key + User Token` · Room-level permissions · `admin` (optional) | Self-hosted: configurable · Default: 200 req/min · WebSocket: unlimited · Version variability | 🔴 High | 🔴 High — Self-hosted: TLS not guaranteed. Auth varies by version. SSO: complex config. Audit trail: instance-dependent | 🟢 Wave 3 |
| 12 | **WhatsApp Business** | Messages received, delivery/read status, template messages, media messages, button replies | Webhook (Cloud API) | ⚠️ `whatsapp_business_messaging` ⚠️ `whatsapp_business_management` ⚠️ Meta Business Verification | Cloud API: 1,000 msg/s · 250 recipients/batch · Template: pre-approval required · Phone number tier limits | 🔴 High | 🔴 High — Meta verification required. GDPR EU: legal tension. Business approval process. Meta accesses metadata | 🟢 Wave 3 |
| 13 | **Viber** | Messages, delivery/seen status, subscriber events, media messages, rich media cards | Webhook | Bot auth token · Public Account required · Partner approval needed | 500 msg/s (Bot API) · 30 msg/s per sender · Public Account: higher limits · Varies by region | 🟡 Med | 🟡 Med — GDPR compliant ✓. Limited enterprise adoption. Partner approval required. Few security audits | 🟢 Wave 3 |

---

## Top-8 Integrations for First Release

Selected by: **audience reach × integration complexity × dev-team value × security risk**

| Rank | Service | Wave | Complexity | Rationale |
|------|---------|------|------------|-----------|
| 🥇 1 | **Slack** | Wave 1 | Med | Most widespread team chat. Mature Events API + Socket Mode. Maximum enterprise audience reach. |
| 🥈 2 | **GitHub** | Wave 1 | Low | Essential for every dev team. Lowest complexity in the list. Fine-grained PAT, minimal security risk. |
| 🥉 3 | **Jira** | Wave 1 | Med | De facto enterprise PM standard. High ROI: issue event aggregation is core unified inbox value. |
| 4 | **GitLab** | Wave 1 | Low | Direct analog to GitHub in complexity. Critical for teams with self-hosted CI/CD pipelines. |
| 5 | **Google Calendar / Meet** | Wave 1 | Med | Meetings-as-context is core inbox value. Push API + SOC 1/2/3. Wide corporate penetration. |
| 6 | **Linear** | Wave 2 | Low | Fast-growing product/dev tool. Best GraphQL API in the list. Simple to integrate, minimal risk. |
| 7 | **Zoom** | Wave 2 | Low | Meeting lifecycle without complex setup. Simple webhook. Wide enterprise market penetration. |
| 8 | **Telegram** | Wave 2 | Low | Simplest auth model (Bot Token, no OAuth). Popular among dev teams for internal notifications. |

---

## Wave Summary

### 🔵 Wave 1 — First release (5 services)

| Service | Key blocker | Implementation note |
|---------|------------|---------------------|
| Slack | OAuth app approval | Socket Mode requires separate app config; Events API for scaling |
| GitHub | Fine-grained PAT scope selection | Use org-level webhook for multi-repo coverage |
| GitLab | Self-hosted vs cloud path split | Detect instance type at onboarding; separate polling fallback for Server |
| Jira | 50 webhook limit per project | Build a webhook multiplexer if serving multiple tenants |
| Google Calendar | Watch channel renewal | Implement cron every 6 days (TTL is 7); silent expiry is a prod risk |

### 🟣 Wave 2 — Second iteration (5 services)

| Service | Key blocker | Implementation note |
|---------|------------|---------------------|
| Discord | Privileged MESSAGE_CONTENT intent | Submit for verification early — review takes 1–3 weeks at >100 servers |
| Linear | None significant | GraphQL — set complexity budget; cache schema introspection |
| MS Teams | Azure AD app + Bot Framework setup | Budget 2–3x dev time vs. a typical webhook integration |
| Zoom | 30 subscription cap per app | Use one app registration per customer tenant if needed |
| Telegram | GDPR compliance posture | Document data handling; do not store message content longer than needed |

### 🟢 Wave 3 — Future (3 services)

| Service | Key blocker | Implementation note |
|---------|------------|---------------------|
| Rocket.Chat | Self-hosted version variability | Negotiate minimum supported version (v5+) with customers |
| WhatsApp Business | Meta Business Verification (1–4 weeks) | Start verification process 1 month before planned launch |
| Viber | Limited enterprise ROI | Evaluate regional demand before investing; Eastern Europe / SEA only |

---

## Hidden Technical Risks

1. **Google Calendar watch TTL** — Watch channels expire after 7 days with no error log. Without a renewal cron, event delivery silently stops in production.

2. **Jira webhook cap** — Cloud limits to 50 registered webhooks per project. At scale with many tenants, a multiplexing proxy layer is required.

3. **Telegram Bot Token** — No OAuth. One compromised token = full bot access. Implement a key rotation policy and per-tenant bot isolation.

4. **Discord privileged intents** — `MESSAGE_CONTENT` requires manual review by Discord at >100 servers. Plan 2–4 weeks lead time. Without it, message text is empty.

5. **WhatsApp template pre-approval** — Every message template must be approved by Meta before use. Rejection is common; build template management into your admin UI.

6. **MS Teams throttling** — The 4 req/s per app/tenant limit is easy to hit in a busy organization. Implement exponential backoff and a queue per tenant from day one.

---

## Recommended Implementation Order (Wave 1)

```
GitHub → GitLab → Slack → Google Calendar → Jira
```

**Rationale:** GitHub and GitLab share nearly identical webhook structures — ship them from one codebase. Slack next for audience impact. Google Calendar before Jira to validate the meeting-context use case early. Jira last due to the Cloud/Server/Data Center path divergence requiring more conditional logic.

---

*Last updated: June 2026 · Version 1.0*
