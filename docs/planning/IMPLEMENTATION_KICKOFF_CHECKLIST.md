# ALLinO Implementation Kickoff Checklist

Цель: быстрый и безопасный старт реализации без потери baseline.
Статус: использовать перед началом первого рабочего дня.

## 1. Scope Lock

- [ ] Подтвержден P0 scope из PREBUILD_SPEC_V1.md.
- [ ] Out-of-scope список согласован и не обсуждается в каждом таске.
- [ ] Wave 1 Core и Wave 1 Optional различаются явно для команды.

## 2. Security Lock

- [ ] Security Gate список виден команде и включен в DoD.
- [ ] Tenant isolation подход зафиксирован (tenant_id + RLS).
- [ ] Секреты и токены не хранятся в репозитории.
- [ ] Определен минимальный audit trail перечень событий.

## 3. Architecture Lock

- [ ] Unified Event Schema v1 утвержден как контракт.
- [ ] Выбран стартовый event bus путь (Redis Streams).
- [ ] Определен минимальный набор таблиц для Sprint 1.
- [ ] Зафиксирована стратегия idempotency/dedup.

## 4. Delivery Readiness

- [ ] Создан Sprint 1 board и назначены владельцы задач.
- [ ] Готов Sprint 2 board как следующий этап.
- [ ] CI baseline включен (lint/test/build).
- [ ] Есть smoke сценарий от ingestion до inbox list.

## 5. UX Readiness

- [ ] Зафиксирован основной shell (Inbox, Focus, Incident, Security, Settings).
- [ ] Определены обязательные error states для Sprint 2.
- [ ] Thread panel и filters входят в рабочий path MVP.

## 6. Design Readiness

- [ ] Variant 1 принят как рабочая визуальная база.
- [ ] WCAG AA требования зафиксированы.
- [ ] Privacy-first UI defaults приняты (без скрытых трекеров).

## 7. Team Agreements

- [ ] Никаких неофициальных API/скрейпинга.
- [ ] Никаких write-back расширений в обход P0.
- [ ] Любое отклонение от baseline фиксируется в change log.

## Exit

- [ ] Все пункты закрыты -> можно стартовать реализацию.
- [ ] Есть незакрытые пункты -> старт только с явным рисковым решением.
