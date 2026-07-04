# 🔐 Security Blueprint: Unified Inbox

**Версия:** 1.0 | **Классификация:** INTERNAL | **Дата:** 2026-06-24
**Цикл пересмотра:** Ежеквартально | **Статус:** DRAFT → требует Security Lead review

---

## 0. Document Metadata

| Поле | Значение |
|---|---|
| Область применения | Unified Inbox (Multi-provider message aggregation) |
| Стандарты | OWASP Top 10, STRIDE, NIST SP 800-53, GDPR Art. 25/32 |
| Ключевые провайдеры | Gmail, Outlook, Slack, Telegram (OAuth 2.0 + PKCE) |
| Среда | Cloud-native, multi-tenant, Zero-Trust |
| Следующий пересмотр | 2026-09-24 |

---

## 1. STRIDE Threat Model

### 1.1 Реестр Критических Активов

| ID | Актив | Классификация | Компонент | Конф-ть | Целостность | Доступность |
|---|---|---|---|---|---|---|
| A-01 | OAuth access / refresh токены | 🔴 CRITICAL | Token Vault | HIGH | HIGH | HIGH |
| A-02 | Содержимое сообщений | 🔴 CONFIDENTIAL | Message Store | HIGH | MEDIUM | MEDIUM |
| A-03 | Ключи шифрования DEK/KEK | 🔴 CRITICAL | KMS / HSM | CRITICAL | CRITICAL | HIGH |
| A-04 | JWT сессионные токены | 🔴 CRITICAL | Auth Service | HIGH | HIGH | HIGH |
| A-05 | Метаданные сообщений | 🟡 SENSITIVE | Message Store | MEDIUM | LOW | LOW |
| A-06 | Аудит-лог | 🔴 CONFIDENTIAL | Audit Store | MEDIUM | CRITICAL | HIGH |
| A-07 | PII пользователей | 🔴 PII/GDPR | User Store | HIGH | MEDIUM | LOW |
| A-08 | API ключи внешних провайдеров | 🔴 CRITICAL | Config Store | HIGH | HIGH | HIGH |
| A-09 | TLS / mTLS сертификаты и ключи | 🔴 CRITICAL | PKI | CRITICAL | CRITICAL | CRITICAL |
| A-10 | Инфраструктурные секреты и конфиги | 🔴 CRITICAL | Ops / Vault | HIGH | HIGH | HIGH |

> **DEK** = Data Encryption Key (per-user, ежегодная ротация)
> **KEK** = Key Encryption Key (per-tenant, 90-дневная ротация)

---

### 1.2 STRIDE Матрица Угроз

| ID | Категория | Угроза | Активы | Вектор атаки | Вер-ть | Ущерб | Риск | Митигация |
|---|---|---|---|---|---|---|---|---|
| T-01 | **S**poofing | Подделка identity сервиса внутри кластера | A-04, A-09 | Скомпрометированный сертификат, MITM | MEDIUM | CRITICAL | 🔴 HIGH | mTLS + SPIFFE/SPIRE |
| T-02 | **S**poofing | Кража OAuth токена → impersonation пользователя | A-01 | XSS, phishing, утечка в logs | HIGH | CRITICAL | 🔴 CRITICAL | Token rotation, encrypted store, CSP |
| T-03 | **T**ampering | Подмена содержимого сообщений при транзите | A-02 | MITM, скомпрометированный прокси | LOW | HIGH | 🟡 MEDIUM | TLS 1.3 everywhere, message signing |
| T-04 | **T**ampering | Модификация / удаление аудит-лога | A-06 | Инсайдер, скомпрометированная БД | LOW | CRITICAL | 🔴 HIGH | Append-only, WORM, HMAC chain |
| T-05 | **T**ampering | SQL/NoSQL инъекция через API | A-02, A-07 | Вредоносный пользовательский ввод | MEDIUM | HIGH | 🔴 HIGH | Parameterized queries, WAF, ORM |
| T-06 | **R**epudiation | Отрицание факта действия пользователем | A-06 | Отсутствие или повреждение логов | MEDIUM | MEDIUM | 🟡 MEDIUM | Иммутабельный audit log, цифровые подписи |
| T-07 | **I**nfo Disclosure | Утечка токенов через URL / query params / logs | A-01, A-04 | HTTP log scraping, Referer header | HIGH | CRITICAL | 🔴 CRITICAL | Tokens only in headers/body, log sanitization |
| T-08 | **I**nfo Disclosure | Verbose error messages → утечка PII / stack trace | A-07 | Любой API endpoint | HIGH | HIGH | 🔴 HIGH | Generic errors в prod, sanitized logging |
| T-09 | **I**nfo Disclosure | Утечка KEK → расшифровка всей базы | A-03 | Скомпрометированный KMS, инсайдер | LOW | CRITICAL | 🔴 HIGH | HSM, envelope encryption, key rotation |
| T-10 | **I**nfo Disclosure | Нарушение tenant isolation (IDOR) | A-02, A-07 | Прямой перебор resource IDs | MEDIUM | CRITICAL | 🔴 HIGH | Row-level security, tenant ID binding в JWT |
| T-11 | **D**enial of Service | Token endpoint flooding / credential stuffing | A-01, A-04 | Brute-force, botnets | HIGH | HIGH | 🔴 HIGH | Rate limiting, CAPTCHA, account lockout |
| T-12 | **D**enial of Service | Webhook / message sync overload | A-02 | Вредоносный payload, webhook flood | MEDIUM | MEDIUM | 🟡 MEDIUM | Payload limits, async queue, circuit breaker |
| T-13 | **E**oP | Горизонтальное перемещение между tenant'ами | A-01, A-02 | IDOR + broken tenancy check | MEDIUM | CRITICAL | 🔴 HIGH | Tenant ID в каждом запросе, RLS в БД |
| T-14 | **E**oP | Admin account takeover | A-10 | Phishing, слабые credentials | MEDIUM | CRITICAL | 🔴 HIGH | MFA обязателен, PAM, JIT access |
| T-15 | **E**oP | JWT claims manipulation (alg:none / HS256) | A-04 | Алгоритм none атака | LOW | CRITICAL | 🔴 HIGH | RS256 only, strict alg validation, reject none |

---

### 1.3 Векторы Атак (Simplified Kill Chain)

| Фаза | Техника | Целевой актив | Индикатор (IOC) |
|---|---|---|---|
| **Initial Access** | OAuth phishing → token theft | A-01 | Логин из нетипичной геолокации/устройства |
| **Initial Access** | XSS → session hijacking | A-04 | CSP violation report в SIEM |
| **Execution** | Malicious webhook payload (RCE attempt) | Backend | Oversized/malformed Content-Type |
| **Persistence** | Refresh token abuse после ревокации | A-01 | Использование токена после logout |
| **Lateral Movement** | IDOR между tenant'ами | A-02, A-07 | tenant_id mismatch в запросе / 403 spike |
| **Exfiltration** | Bulk export через API пагинацию | A-02 | Аномально большой объём выгрузки за сессию |
| **Impact** | Unauthorised KMS key operation | A-03 | Попытка удаления/деактивации key |
| **Impact** | Truncate / DELETE аудит-лога | A-06 | DDL-команда на audit-таблице |

---

## 2. Data Flow

### 2.1 Архитектурный Data Flow (Zero-Trust)

```
┌───────────────────────────────────────────────────────────────────────┐
│                  UNIFIED INBOX — ZERO-TRUST DATA FLOW                  │
└───────────────────────────────────────────────────────────────────────┘

  ┌────────────────────┐
  │  CLIENT             │  Browser / Mobile App
  │  ┌──────────────┐  │  → CSP, HSTS, Certificate Pinning (mobile)
  │  │ Local Cache  │  │  → IndexedDB / Keychain: AES-256-GCM
  │  │ (AES-256)    │  │  → JWT: memory ONLY (no localStorage)
  │  └──────────────┘  │  → Auto-logout at 15 min idle
  └────────┬────────────┘
           │ TLS 1.3 + HSTS
           ▼
  ┌────────────────────────────────────────────┐
  │  EDGE / CDN                                  │
  │  Cloudflare · WAF (OWASP CRS)                │
  │  DDoS Protection · Bot Management            │
  │  IP Reputation · Rate Limit (global)         │
  └─────────────────┬──────────────────────────┘
                    │ TLS 1.3
                    ▼
  ┌────────────────────────────────────────────┐
  │  API GATEWAY                                 │
  │  JWT Verify · Per-user Rate Limit            │
  │  CORS Whitelist · Request Schema Validation  │
  │  Tenant ID Injection from JWT claims         │
  └────────┬───────────────┬────────────────────┘
           │ mTLS           │ mTLS
           ▼               ▼
  ┌──────────────┐  ┌───────────────────────────────────────┐
  │  AUTH        │  │  MESSAGE SERVICE                       │
  │  SERVICE     │  │  Router · Normalizer · Encrypt Layer   │
  │  JWT + OAuth │  └───────┬────────────────┬──────────────┘
  │  PKCE Flow   │          │ mTLS           │ mTLS
  └──────┬───────┘          ▼               ▼
         │ mTLS    ┌─────────────────┐  ┌───────────────────┐
         ▼         │  PROVIDER        │  │  MESSAGE QUEUE     │
  ┌─────────────┐  │  CONNECTORS      │  │  Kafka / RabbitMQ  │
  │  TOKEN      │  │  ┌────────────┐  │  │  Encrypted at-rest │
  │  VAULT      │  │  │Gmail/OAuth │  │  └────────┬──────────┘
  │  HashiCorp  │  │  ├────────────┤  │           │
  │  Vault+HSM  │  │  │Outlook/O365│  │           ▼
  └─────────────┘  │  ├────────────┤  │  ┌────────────────────┐
                   │  │Slack/Tg    │  │  │  MESSAGE STORE      │
                   │  └────────────┘  │  │  PostgreSQL         │
                   └─────────────────┘  │  AES-256-GCM (field) │
                                        │  Row-Level Security   │
                                        └────────┬─────────────┘
       ┌─────────────────────────────────────────│──────────┐
       │ mTLS                                    │          │
       ▼                                         ▼          ▼
  ┌──────────────┐                    ┌──────────────┐  ┌──────────────┐
  │  ADMIN SVC   │                    │  KMS          │  │  AUDIT STORE │
  │  RBAC + MFA  │                    │  Envelope Enc │  │  Append-Only │
  │  PAM, JIT    │                    │  DEK→KEK→HSM  │  │  HMAC Chain  │
  └──────────────┘                    └──────────────┘  │  WORM/S3 Lock│
                                                         └──────────────┘

  ЛЕГЕНДА:
  ─────── TLS 1.3 (внешний трафик)
  ═══════ mTLS (внутренний zero-trust, SPIFFE SVID identity)
  DEK     Data Encryption Key — per user
  KEK     Key Encryption Key — per tenant, managed by KMS
  HSM     Hardware Security Module — master key never leaves HSM
```

---

### 2.2 OAuth 2.0 + PKCE Token Flow

```
  Пользователь    API Gateway     Auth Service    Token Vault     Provider
      │                │                │               │             │
      │─ Connect ──────▶               │               │             │
      │                │─ Forward ──────▶               │             │
      │                │                │─ Gen PKCE ─   │             │
      │                │                │  code_verifier│             │
      │                │                │  code_challenge (S256)      │
      │◀─── Redirect to Provider OAuth ────────────────────────────────│
      │─ User grants permissions ────────────────────────────────────▶ │
      │◀─── auth_code + state ─────────────────────────────────────── │
      │─ auth_code ────▶               │               │             │
      │                │─ Verify state ▶               │             │
      │                │                │─ Exchange code + verifier ──▶│
      │                │                │◀── access_token + refresh ───│
      │                │                │─ Encrypt ────▶│             │
      │                │                │  & store token│             │
      │◀─ 200 OK ──────│◀─ Success ─────│               │             │

  ⚠️  ПРАВИЛА ТОКЕНОВ:
  1. code_verifier НИКОГДА не передаётся по сети (PKCE S256)
  2. access_token НИКОГДА не хранится на клиенте
  3. Vault хранит только зашифрованные токены (AES-256)
  4. Refresh rotation: каждый use → новый refresh_token (старый инвалидируется)
  5. state parameter проверяется (CSRF protection)
  6. Token binding к User-Agent + IP (soft check, alert on mismatch)
```

---

## 3. Security Controls по Слоям

### 3.1 Client Layer

| ID | Контроль | Угроза | Реализация | Критерий готовности |
|---|---|---|---|---|
| CL-01 | Content Security Policy (CSP) | T-02 XSS | `default-src 'self'`; no `unsafe-inline`; `report-uri` активен | Grade A на securityheaders.com; 0 violations в prod |
| CL-02 | JWT только в памяти (не в localStorage) | T-02, T-07 | Token в JS closure / httpOnly Secure cookie; sessionStorage запрещён | Pentest не обнаруживает токен через storage API |
| CL-03 | HTTPS Strict + HSTS Preload | T-03 MITM | `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` | Домен включён в HSTS preload list |
| CL-04 | Certificate Pinning (mobile) | T-01, T-03 | iOS: TrustKit; Android: OkHttp network security config | Блокирует подмену сертификата в тесте |
| CL-05 | Локальное шифрование кэша | T-09 Physical | AES-256-GCM через WebCrypto API / iOS Keychain / Android Keystore | Данные нечитаемы без device unlock |
| CL-06 | Auto-logout при бездействии | T-02 Session | 15 мин idle → token revoke + clear memory | Подтверждено функциональным тестом |
| CL-07 | DOMPurify sanitization HTML email | T-05 XSS | DOMPurify для рендеринга HTML-содержимого писем | OWASP ZAP scan: 0 XSS findings |
| CL-08 | Subresource Integrity (SRI) | Supply chain | `integrity="sha384-..."` на все CDN/external ресурсы | Все external scripts имеют SRI hash |

---

### 3.2 Backend Layer

| ID | Контроль | Угроза | Реализация | Критерий готовности |
|---|---|---|---|---|
| BE-01 | JWT RS256; строгая валидация `alg` | T-15 EoP | RS256 only; reject `alg:none`, `HS256`; проверка `exp`, `iss`, `aud` | Тест: `alg:none` → 401; истёкший → 401 |
| BE-02 | Refresh Token Rotation + theft detection | T-02 | Каждый use инвалидирует старый токен; reuse → revoke all sessions | Повторное использование old token → revoke + alert |
| BE-03 | Rate Limiting per user + per IP | T-11 DoS | Auth: 5 req/min; API: 100 req/min; lockout после 10 failed | Rate limit срабатывает в нагрузочном тесте |
| BE-04 | Input Validation (schema-based, whitelist) | T-05 Inject | Zod/Joi/Pydantic на каждый endpoint; reject unexpected fields | Fuzz test не вызывает 500 ошибок |
| BE-05 | Tenant Isolation: tenantId из JWT, не request | T-10, T-13 | `tenantId` извлекается ТОЛЬКО из JWT claims; RLS на уровне БД | Pentest: нет IDOR между tenant'ами |
| BE-06 | Нет hardcoded secrets (Vault everywhere) | T-01 | HashiCorp Vault dynamic secrets; env vars только для Vault addr | `gitleaks detect`: 0 findings в git history |
| BE-07 | Dependency scanning в CI (SCA) | Supply chain | Snyk/Dependabot; pipeline block на Critical CVE | CI fails при Critical CVE в зависимостях |
| BE-08 | CORS Whitelist; no wildcard в prod | T-02 CSRF | Список разрешённых origins; `credentials: true` только для своих доменов | Config review: нет `*` в prod CORS |
| BE-09 | Sanitized error responses | T-08 Disclosure | Prod: generic error + `error_id`; stack trace только во внутренних logs | Pentest: нет PII / stack trace в 4xx/5xx |
| BE-10 | Message payload size limits | T-12 DoS | Attachment max 50MB; request body max 1MB | Oversized request → 413 немедленно; no OOM |

---

### 3.3 Storage Layer

| ID | Контроль | Угроза | Реализация | Критерий готовности |
|---|---|---|---|---|
| ST-01 | Шифрование at-rest: Envelope Encryption | T-09 | AES-256-GCM; DEK per user → KEK per tenant (KMS) → Master Key (HSM) | Прямой запрос к диску/файлам: только ciphertext |
| ST-02 | Field-level encryption для PII и body | T-09, T-10 | `message_body`, `subject`, `from_address`, `to_address` — encrypted columns | SELECT в БД: encrypted columns возвращают ciphertext |
| ST-03 | Row-Level Security (PostgreSQL RLS) | T-10, T-13 | `SET app.current_tenant_id = $1` + RLS policy на каждой таблице | User из tenant A не видит данные tenant B |
| ST-04 | Отдельный DB user per сервис (least priv) | T-04, T-13 | message_svc: SELECT+INSERT; admin_svc: +UPDATE; audit_svc: INSERT only | DB credentials per service в Vault |
| ST-05 | Append-only Audit Log (HMAC chain) | T-04, T-06 | Отдельная БД; INSERT-only роль; HMAC на каждой строке; chain validation | UPDATE/DELETE на audit таблице → permission denied |
| ST-06 | WORM backup для Audit Store | T-04 Tamper | S3 Object Lock (Compliance mode) / Azure Immutable Blob Storage | Попытка удалить audit backup → error |
| ST-07 | Шифрование резервных копий | T-09 | pgBackRest с AES-256; ключи бэкапов хранятся отдельно от данных | Бэкап без ключа нерасшифруем |
| ST-08 | Automated Key Rotation Policy | T-09 | DEK: ежегодно; KEK: 90 дней; автоматическая re-encryption при ротации | Rotation job: 0 downtime; валидация после ротации |

---

### 3.4 Network Layer

| ID | Контроль | Угроза | Реализация | Критерий готовности |
|---|---|---|---|---|
| NW-01 | TLS 1.3 на всех внешних endpoints | T-03 MITM | Min TLS 1.2 (deprecated 2027); TLS 1.0/1.1 disabled; ECDHE cipher only | `testssl.sh`: A+ рейтинг; no weak ciphers |
| NW-02 | mTLS между всеми internal сервисами | T-01, T-03 | Istio / Linkerd service mesh; SPIFFE SVID как crypto identity | Трафик без valid cert → connection refused |
| NW-03 | Network Segmentation (VPC/Subnet) | T-13 | Prod/Staging/Dev в отдельных VPC; DB в private subnet (no public IP) | Nmap: DB endpoint недоступен из internet |
| NW-04 | WAF (Web Application Firewall) | T-05, T-11 | OWASP Core Rule Set (CRS); custom rules для OAuth endpoints | WAF блокирует SQLi/XSS/path traversal в тесте |
| NW-05 | DDoS Protection (L3/L4/L7) | T-11, T-12 | Cloudflare / AWS Shield Advanced; adaptive rate limiting на edge | DDoS симуляция: availability не нарушена |
| NW-06 | Zero-Trust Network Access (ZTNA) для admin | T-14 | Infra admin доступ только через ZTNA + MFA; no SSH from internet | SSH/RDP без ZTNA клиента недоступны |
| NW-07 | Egress Filtering (outbound whitelist) | Exfiltration | Whitelist провайдеров (Google/Microsoft/Slack API hostnames); block unexpected | Outbound трафик только к approved API endpoints |
| NW-08 | DNS Security (DNSSEC) | T-01, T-03 | DNSSEC на домене; DNS-over-HTTPS для internal resolution | DNSSEC validation активен; `dig +dnssec` → AD flag |

---

### 3.5 Ops Layer

| ID | Контроль | Угроза | Реализация | Критерий готовности |
|---|---|---|---|---|
| OP-01 | SIEM + IOC Alerting | Все | ELK/Splunk; алерты по §1.3 IOC; MTTR target < 15 min (SEV-1) | Тестовый алерт срабатывает < 5 min |
| OP-02 | MFA обязателен для всех admin | T-14 | TOTP / FIDO2 / hardware key; bypass MFA = невозможно в prod | Audit: 100% admin аккаунтов с MFA |
| OP-03 | Least Privilege + Just-In-Time access | T-14 | RBAC; PAM (Teleport/BeyondTrust); 0 standing admin privileges | JIT session audit: доступ выдаётся на время задачи |
| OP-04 | CI/CD Security Gates | Supply chain | SAST (Semgrep), DAST (OWASP ZAP), SCA (Snyk) в pipeline | Pipeline fail при HIGH+ уязвимости |
| OP-05 | Secrets scanning в git (pre-commit + CI) | T-01 | gitleaks + git-secrets pre-commit hook; также в CI pipeline | `gitleaks detect`: 0 findings |
| OP-06 | Vulnerability Management SLA | Все | Critical: patch 24h; High: 72h; Medium: 7 дней | SLA соблюдается в 95%+ случаев (tracked) |
| OP-07 | Quarterly Penetration Testing | Все | External WAPT + internal red team; scope: OAuth flows, IDOR, auth | Pentest report: 0 Critical/High открытых findings |
| OP-08 | Immutable Infrastructure + Image Signing | Supply chain | Container images подписаны (Cosign/Notary); no SSH в prod pods | `kubectl exec` / SSH в prod → запрещено policy |
| OP-09 | Log retention + immutability | T-04, T-06 | Logs shipped to immutable store; 1 год minimum; no app-level delete | Logs нельзя удалить через app credentials |
| OP-10 | SBOM generation (Software Bill of Materials) | Supply chain | CycloneDX SBOM при каждом build; хранится с release артефактами | SBOM актуален и доступен для каждого release |

---

## 4. Security Baseline — Приоритеты P0 / P1 / P2

| Приоритет | ID | Контроль | Угроза | Критерий готовности | Дедлайн |
|---|---|---|---|---|---|
| 🔴 **P0** | BE-01 | JWT RS256 + строгая валидация `alg` | T-15 CRITICAL EoP | `alg:none` → 401; тест автоматизирован | До первого деплоя |
| 🔴 **P0** | BE-05 | Tenant isolation (JWT + RLS) | T-10, T-13 CRITICAL | Pentest: нет IDOR между tenant'ами | До первого деплоя |
| 🔴 **P0** | ST-01 | Шифрование at-rest AES-256 (envelope) | T-09 CRITICAL | SELECT в БД: ciphertext, не plaintext | До первого деплоя |
| 🔴 **P0** | NW-01 | TLS 1.3 everywhere (external) | T-03 | testssl.sh A+; TLS 1.0/1.1 disabled | До первого деплоя |
| 🔴 **P0** | CL-01 | Content Security Policy (CSP) | T-02 CRITICAL | Grade A; 0 violations в prod | До первого деплоя |
| 🔴 **P0** | BE-06 | Нет hardcoded secrets (Vault) | T-01 CRITICAL | gitleaks: 0 findings в git history | До первого деплоя |
| 🔴 **P0** | CL-03 | HSTS Preload | T-03 | Включён в preload list; `max-age=31536000` | До первого деплоя |
| 🔴 **P0** | OP-02 | MFA для всех admin аккаунтов | T-14 CRITICAL | Audit: 100% admin с MFA | До первого деплоя |
| 🔴 **P0** | ST-05 | Append-only Audit Log | T-04, T-06 | DELETE → permission denied (тест) | До первого деплоя |
| 🔴 **P0** | BE-03 | Rate Limiting auth endpoints | T-11 | Брутфорс заблокирован в нагрузочном тесте | До первого деплоя |
| 🟠 **P1** | NW-02 | mTLS между всеми сервисами | T-01, T-03 | Весь inter-service трафик mTLS | Sprint +1 |
| 🟠 **P1** | BE-02 | Refresh Token Rotation + theft detection | T-02 CRITICAL | Reuse → revoke all sessions + alert | Sprint +1 |
| 🟠 **P1** | ST-02 | Field-level encryption PII | T-09 | PII columns: encrypted в БД | Sprint +1 |
| 🟠 **P1** | NW-04 | WAF (OWASP CRS) | T-05, T-11 | WAF активен; SQLi тест блокирован | Sprint +1 |
| 🟠 **P1** | OP-04 | CI/CD security gates (SAST/SCA) | Supply chain | Pipeline fail на HIGH CVE | Sprint +1 |
| 🟠 **P1** | BE-09 | Sanitized error responses | T-08 | Нет PII / stack trace в prod ошибках | Sprint +1 |
| 🟠 **P1** | ST-03 | Row-Level Security PostgreSQL | T-10, T-13 | RLS policy активна на всех таблицах | Sprint +1 |
| 🟠 **P1** | OP-01 | SIEM + IOC Alerting | Все | Тестовый алерт: < 5 min | Sprint +2 |
| 🟠 **P1** | NW-03 | Network Segmentation (VPC) | T-13 | DB subnet изолирован; no public IP | Sprint +1 |
| 🟠 **P1** | CL-07 | DOMPurify sanitization HTML email | T-05 XSS | ZAP scan: 0 XSS findings | Sprint +1 |
| 🟡 **P2** | OP-07 | Quarterly Pentest (external WAPT) | Все | 1й pentest: 0 Critical/High open | 3 мес после релиза |
| 🟡 **P2** | CL-04 | Certificate Pinning (mobile) | T-01, T-03 | Blocking при подмене cert в тесте | Sprint +3 |
| 🟡 **P2** | ST-08 | Automated Key Rotation | T-09 | DEK/KEK ротация без downtime | 1 мес после релиза |
| 🟡 **P2** | OP-08 | Immutable Infrastructure + Cosign | Supply chain | SSH в prod pod: запрещено | Sprint +3 |
| 🟡 **P2** | NW-07 | Egress Filtering (whitelist) | Exfiltration | Outbound только к approved endpoints | Sprint +3 |
| 🟡 **P2** | OP-10 | SBOM generation (CycloneDX) | Supply chain | SBOM в каждом release | Sprint +3 |
| 🟡 **P2** | NW-08 | DNSSEC | T-01, T-03 | DNSSEC validation активен | 2 мес после релиза |
| 🟡 **P2** | OP-03 | JIT admin access (PAM) | T-14 | 0 standing admin priv | Sprint +4 |

---

## 5. Go / No-Go Checklist (Pre-Release)

> **✅ GO:** все чекбоксы отмечены
> **🚫 NO-GO:** любой пункт 1–21 не выполнен — деплой заблокирован

### 🔐 Аутентификация и Авторизация

| # | Проверка | Риск | Критерий GO | ✓ |
|---|---|---|---|---|
| 1 | JWT использует RS256; `alg:none` отклонён | T-15 CRITICAL | Автотест: `alg:none` → 401 | ☐ |
| 2 | Access token: expiry 15 мин; хранится только в памяти | T-02, T-07 | Pentest: токен не найден в localStorage/cookie | ☐ |
| 3 | Refresh token rotation при каждом use | T-02 | Тест: старый refresh после use → 401 | ☐ |
| 4 | MFA обязателен для всех admin аккаунтов | T-14 | Audit: 0 admin без MFA | ☐ |
| 5 | OAuth PKCE (S256) реализован | T-02 | Обмен кода без code_verifier → rejected | ☐ |

### 🏢 Multi-Tenancy и Изоляция

| # | Проверка | Риск | Критерий GO | ✓ |
|---|---|---|---|---|
| 6 | `tenantId` берётся из JWT claims, НЕ из request body | T-13 CRITICAL | Code review подтверждён + тест | ☐ |
| 7 | PostgreSQL RLS включён на всех таблицах | T-10, T-13 | Тест: User-A не видит данные User-B | ☐ |
| 8 | IDOR scan пройден (automated или pentest) | T-10 | Automated IDOR scan: 0 findings | ☐ |

### 🔑 Секреты и Шифрование

| # | Проверка | Риск | Критерий GO | ✓ |
|---|---|---|---|---|
| 9 | 0 hardcoded secrets в git (gitleaks scan) | T-01, T-09 CRITICAL | `gitleaks detect`: 0 findings | ☐ |
| 10 | Все секреты через HashiCorp Vault | T-01 | Env vars: только Vault addr + app_role ID | ☐ |
| 11 | Данные в БД зашифрованы at-rest (AES-256) | T-09 | Прямой SELECT в БД → ciphertext | ☐ |
| 12 | PII-поля зашифрованы на уровне column | T-09 | Audit PII columns: все encrypted | ☐ |

### 🌐 Сеть и Транспорт

| # | Проверка | Риск | Критерий GO | ✓ |
|---|---|---|---|---|
| 13 | TLS 1.3 на всех внешних эндпоинтах | T-03 | `testssl.sh`: A+; TLS 1.0/1.1 disabled | ☐ |
| 14 | HSTS включён (+ preload) | T-03 | Header присутствует; `max-age=31536000; preload` | ☐ |
| 15 | WAF активен (OWASP CRS) | T-05, T-11 | WAF тест: SQLi и XSS векторы заблокированы | ☐ |
| 16 | DB в изолированной подсети (no public IP) | T-13 | Nmap: DB endpoint недостижим из internet | ☐ |
| 17 | CORS: нет `*` в prod конфигурации | T-02 | Config review: whitelist origins only | ☐ |

### 📋 Аудит и Логирование

| # | Проверка | Риск | Критерий GO | ✓ |
|---|---|---|---|---|
| 18 | Audit log append-only (DELETE → forbidden) | T-04, T-06 | Тест: DELETE на audit table → permission denied | ☐ |
| 19 | Логи не содержат токены / пароли / PII | T-07 CRITICAL | Log sampling: 0 sensitive values в logs | ☐ |
| 20 | SIEM алерты настроены (критические IOC из §1.3) | Все | Test alert: срабатывает < 5 min | ☐ |
| 21 | Log retention ≥ 1 год (GDPR compliance) | T-06 | Logs archived с immutable storage | ☐ |

### 🏗️ CI/CD и Supply Chain

| # | Проверка | Риск | Критерий GO | ✓ |
|---|---|---|---|---|
| 22 | SAST (Semgrep) в pipeline; блокирует HIGH+ | Supply chain | Pipeline: 0 пропущенных HIGH findings | ☐ |
| 23 | SCA (Snyk) блокирует Critical CVE | Supply chain | Нет known Critical CVE в зависимостях | ☐ |
| 24 | Dependency lock files в VCS | Supply chain | `package-lock.json` / `poetry.lock` актуальны | ☐ |

### 🚨 Incident Readiness

| # | Проверка | Риск | Критерий GO | ✓ |
|---|---|---|---|---|
| 25 | IR Runbook задокументирован и доступен on-call | Все | Runbook в wiki; команда ознакомлена | ☐ |
| 26 | Token revocation endpoint работает корректно | T-02 | Тест: revoke → следующий request → 401 | ☐ |
| 27 | Backup restore тест пройден (RTO < 4h) | DR | Full restore: завершён за < RTO | ☐ |
| 28 | On-call ротация настроена (PagerDuty/OpsGenie) | Все | Тест алерт: on-call получает notification | ☐ |
| 29 | GDPR Data Processing Agreement актуален | GDPR/Legal | Legal review: approved; DPA подписан | ☐ |

---

## 6. Incident Response Policy

### 6.1 Severity Matrix

| Severity | Описание | Примеры | Notify SLA | Contain SLA |
|---|---|---|---|---|
| 🔴 **SEV-1** | Критический: данные под угрозой | OAuth token leak, tenant isolation breach, KMS compromise | < 15 min | < 1 hr |
| 🟠 **SEV-2** | Серьёзный: частичная компрометация | Admin account takeover, audit log tampering attempt, массовые failed logins | < 30 min | < 4 hr |
| 🟡 **SEV-3** | Подозрительная активность, ущерба нет | Аномальный трафик, необычная геолокация, rate limit abuse | < 1 hr | < 8 hr |
| ⚪ **SEV-4** | Информационный | Уязвимость в зависимости (Medium), failed logins ниже порога | < 24 hr | < 72 hr |

---

### 6.2 IR Phases (NIST SP 800-61)

| Фаза | Действия | Ответственный | Инструменты |
|---|---|---|---|
| **1. Detect** | SIEM alert / user report; подтверждение severity | On-call engineer | SIEM, PagerDuty/OpsGenie |
| **2. Triage** | Определить scope: какие активы и пользователи затронуты; собрать доказательства | Security Lead | Kibana/Splunk, audit logs |
| **3. Contain** | Revoke tokens; block malicious IP; isolate affected tenant; disable compromised account | DevOps + Security | Vault CLI, WAF, K8s NetworkPolicy |
| **4. Eradicate** | Удалить вектор: патч, ротация ключей, удаление злоумышленника | Dev + Security | Patch pipeline, KMS rotate |
| **5. Recover** | Восстановление: restore from backup, re-enable с новыми credentials | DevOps | DR runbook, pgBackRest |
| **6. Post-Incident** | RCA; обновление runbook; GDPR notification если требуется; lessons learned | All | Confluence/Notion |

---

### 6.3 GDPR / Регуляторные Уведомления

| Ситуация | Действие | Дедлайн |
|---|---|---|
| Подтверждённая утечка PII | Уведомить DPA (UODO в Польше) | **< 72 часа** |
| Утечка PII > 250 пользователей | Уведомить DPA + уведомление пользователям | **< 72 часа** |
| OAuth token leak | Уведомить затронутых пользователей | **< 24 часа** |
| KMS / ключи компрометированы | Emergency re-encryption + notify регулятора | **Немедленно** |
| Admin account compromise | Internal notify + audit все действия аккаунта | **< 1 hr** |

---

### 6.4 Сценарии Containment (Quick Reference)

| Сценарий | Шаги containment | Vault команда / Action |
|---|---|---|
| OAuth token leak | Revoke все токены пользователя | `vault lease revoke -prefix auth/oauth/user/{id}` |
| Mass token compromise | Kill-switch: revoke все OAuth tokens | `vault lease revoke -prefix auth/oauth/` |
| Compromised service account | Rotate Vault approle secret_id | `vault write -f auth/approle/role/{svc}/secret-id` |
| Active intrusion (lateral movement) | Isolate pod / kill sessions | `kubectl delete pod {pod}` + WAF IP block |
| Audit log tampering attempt | Alert + lock audit DB access | Revoke audit DB user session |

---

## 7. Backup & Disaster Recovery Policy

### 7.1 RPO / RTO Targets

| Компонент | RPO (макс. потеря данных) | RTO (макс. время восстановления) | Стратегия |
|---|---|---|---|
| Message Store (PostgreSQL) | **1 час** | **4 часа** | WAL streaming → S3; daily full backup |
| Token Vault (HashiCorp) | **0** (HA cluster) | **30 мин** | Raft consensus; multi-AZ auto-failover |
| Audit Store | **0** (append + replication) | **1 час** | Streaming replica + WORM S3 backup |
| KMS / HSM | **0** (HA HSM cluster) | **15 мин** | HSM cluster; key escrow в sealed envelope |
| Message Queue (Kafka) | **15 мин** | **2 часа** | Replication factor 3; topic S3 offload |

---

### 7.2 Backup Schedule & Policy

| Компонент | Частота | Тип | Шифрование | Retention | Хранилище |
|---|---|---|---|---|---|
| PostgreSQL | WAL streaming (непрерывно) + daily full | Incremental + Full | AES-256 (отдельный key) | 30 дней daily; 1 год weekly | S3 (отдельный аккаунт) |
| Audit Store | Real-time реплика + daily full | Full | AES-256 | **7 лет** (GDPR Art. 17) | S3 Object Lock (Compliance) |
| Vault snapshots | Daily | Full | Vault native seal | 90 дней | S3 (отдельный аккаунт) |
| Config / Secrets | При каждом изменении | Version-controlled | Vault transit encryption | 1 год | Vault + git (encrypted refs) |
| Kafka topics | Continuous replication | Streaming | Kafka at-rest AES-256 | 7 дней hot; S3 offload 1 год | In-cluster + S3 |

---

### 7.3 Recovery Runbook (Scenarios)

| Сценарий | Шаги восстановления | RTO Target | Ответственный |
|---|---|---|---|
| **DB Corruption** | 1. Stop writes → 2. pgBackRest restore → 3. Apply WAL → 4. Validate → 5. Resume | < 4 hr | DBA + DevOps |
| **KMS Compromise** | 1. Rotate master key → 2. Re-encrypt все DEKs → 3. Revoke старые KEKs → 4. Audit logs | < 2 hr | Security + DBA |
| **Region Failure** | 1. DNS failover → 2. Cross-region restore → 3. Validate integrity → 4. Monitor | < 8 hr | DevOps |
| **OAuth Mass Leak** | 1. Revoke все tokens (Vault) → 2. Force re-auth всех users → 3. Rotate client secrets → 4. Notify | < 1 hr | Security + DevOps |
| **Ransomware** | 1. Isolate сеть → 2. Preserve evidence → 3. Restore immutable backup → 4. Notify DPA | < 24 hr | All teams |

---

### 7.4 DR Testing Schedule

| Тест | Частота | Критерий успеха |
|---|---|---|
| Backup restore (full PostgreSQL) | Ежемесячно | Restore < RTO; данные консистентны после restore |
| Automatic failover (primary DB → replica) | Ежеквартально | Failover < 60 сек; 0 data loss |
| Cross-region DR drill | Раз в полгода | Полный сервис восстановлен < 8 hr |
| IR tabletop exercise | Ежеквартально | Команда знает роли; runbook актуален |
| Key rotation drill | Ежемесячно | Rotation без downtime; 0 decryption errors |
| Token revocation mass test | До каждого major release | 100% tokens revoked < 60 сек |

---

## Appendix A: Security Contacts & Escalation Matrix

| Роль | Ответственность | Escalation |
|---|---|---|
| Security Lead | IR coordination, threat model reviews, pentest | → CTO |
| On-Call DevOps | First responder, containment, infra | → Security Lead |
| DBA | DB restore, key operations | → Security Lead |
| Legal / DPO | GDPR notification, DPA communications | → CEO |
| Provider Contact | OAuth issues with Gmail/Outlook/Slack APIs | External support channels |

---

## Appendix B: Полезные Команды (Quick Reference)

```bash
# Проверка TLS
testssl.sh --full https://inbox.yourdomain.com

# Поиск secrets в git
gitleaks detect --source . --verbose

# Проверка CSP headers
curl -I https://inbox.yourdomain.com | grep -i content-security

# PostgreSQL: проверка RLS
SET app.current_tenant_id = 'tenant-A';
SELECT COUNT(*) FROM messages; -- должно вернуть только messages tenant-A

# Vault: revoke токены пользователя
vault lease revoke -prefix auth/oauth/user/<user_id>

# Проверка mTLS (inter-service)
istioctl authn tls-check <pod-name> <service-name>
```

---

*Статус: DRAFT | Следующий review: 2026-09-24 | Владелец: Security Architecture*
*Требует review от: Security Lead + Legal/DPO перед финализацией*
