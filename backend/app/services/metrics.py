from dataclasses import dataclass
from threading import Lock


@dataclass
class SourceMetrics:
    sync_count: int = 0
    processed: int = 0
    inserted: int = 0
    duplicates: int = 0
    rejected: int = 0
    total_lag_ms: float = 0.0
    lag_samples: int = 0
    retry_count: int = 0
    last_health: str = "unknown"


class MetricsStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sources_by_tenant: dict[str, dict[str, SourceMetrics]] = {}

    def record_sync(
        self,
        tenant_id: str,
        source: str,
        processed: int,
        inserted: int,
        duplicates: int,
        rejected: int,
        total_lag_ms: float,
        lag_samples: int,
        health: str,
        retry_count: int = 0,
    ) -> None:
        with self._lock:
            tenant_sources = self._sources_by_tenant.setdefault(tenant_id, {})
            m = tenant_sources.setdefault(source, SourceMetrics())
            m.sync_count += 1
            m.processed += processed
            m.inserted += inserted
            m.duplicates += duplicates
            m.rejected += rejected
            m.total_lag_ms += total_lag_ms
            m.lag_samples += lag_samples
            m.retry_count += retry_count
            m.last_health = health

    def snapshot(self, tenant_id: str) -> dict:
        with self._lock:
            result: dict = {}
            for source, m in self._sources_by_tenant.get(tenant_id, {}).items():
                avg_lag = m.total_lag_ms / m.lag_samples if m.lag_samples > 0 else 0.0
                result[source] = {
                    "sync_count": m.sync_count,
                    "processed": m.processed,
                    "inserted": m.inserted,
                    "duplicates": m.duplicates,
                    "rejected": m.rejected,
                    "avg_lag_ms": round(avg_lag, 1),
                    "retry_count": m.retry_count,
                    "last_health": m.last_health,
                }
            return result


_store = MetricsStore()


def get_metrics_store() -> MetricsStore:
    return _store
