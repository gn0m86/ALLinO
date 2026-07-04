import {
  AuditLogEntry,
  ChannelSummary,
  ConnectorCapability,
  DigestResponse,
  GenericConnectorConfig,
  GenericConnectorCreateInput,
  GenericConnectorUpdateInput,
  InboxPageResponse,
  ConnectorRun,
  ConnectorStatus,
  InboxMessage,
  ReplyResponse,
} from "./types";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";
const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID ?? "tenant_demo";

export const RUNTIME_CONFIG = {
  backendUrl: BACKEND_URL,
  tenantId: TENANT_ID,
};

const API_KEY_STORAGE_KEY = "allino_api_key";

export function getStoredApiKey(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(API_KEY_STORAGE_KEY);
}

export function setStoredApiKey(apiKey: string | null): void {
  if (typeof window === "undefined") return;
  if (apiKey) {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, apiKey);
  } else {
    window.localStorage.removeItem(API_KEY_STORAGE_KEY);
  }
}

function baseHeaders(extra?: Record<string, string>): Record<string, string> {
  const apiKey = getStoredApiKey();
  return {
    "X-Tenant-Id": TENANT_ID,
    ...(apiKey ? { "X-API-Key": apiKey } : {}),
    ...extra,
  };
}

export async function searchMessages(
  query: string,
  signal?: AbortSignal,
): Promise<InboxMessage[]> {
  const url = new URL("/api/v1/ingestion/search", BACKEND_URL);
  url.searchParams.set("q", query);

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Search failed: ${response.status}`);
  }

  return response.json();
}

export async function fetchDigest(
  hours = 24,
  signal?: AbortSignal,
): Promise<DigestResponse> {
  const url = new URL("/api/v1/ingestion/digest", BACKEND_URL);
  url.searchParams.set("hours", String(hours));

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to load digest: ${response.status}`);
  }

  return response.json();
}

export async function fetchChannels(
  source?: string,
  signal?: AbortSignal,
): Promise<ChannelSummary[]> {
  const url = new URL("/api/v1/ingestion/channels", BACKEND_URL);
  if (source) url.searchParams.set("source", source);

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to load channels: ${response.status}`);
  }

  return response.json();
}

export async function fetchThreadMessages(
  threadKey: string,
  signal?: AbortSignal,
): Promise<InboxMessage[]> {
  const url = new URL(
    `/api/v1/ingestion/threads/${encodeURIComponent(threadKey)}/messages`,
    BACKEND_URL,
  );

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to load thread messages: ${response.status}`);
  }

  return response.json();
}

export async function markThreadRead(
  threadKey: string,
  signal?: AbortSignal,
): Promise<void> {
  const url = new URL(
    `/api/v1/ingestion/threads/${encodeURIComponent(threadKey)}/read`,
    BACKEND_URL,
  );

  const response = await fetch(url.toString(), {
    method: "POST",
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to mark thread as read: ${response.status}`);
  }
}

export async function fetchRocketchatDmTimezone(
  roomId: string,
  signal?: AbortSignal,
): Promise<number | null> {
  const url = new URL("/api/v1/ingestion/rocketchat/dm-timezone", BACKEND_URL);
  url.searchParams.set("room_id", roomId);

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    return null;
  }

  const data = await response.json();
  return typeof data?.utc_offset_hours === "number" ? data.utc_offset_hours : null;
}

export async function fetchRocketchatOwnUsername(signal?: AbortSignal): Promise<string | null> {
  const url = new URL("/api/v1/ingestion/rocketchat/me", BACKEND_URL);

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    return null;
  }

  const data = await response.json();
  return typeof data?.username === "string" ? data.username : null;
}

export async function fetchInbox(
  signal?: AbortSignal,
): Promise<InboxMessage[]> {
  const url = new URL("/api/v1/ingestion/inbox", BACKEND_URL);

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to load inbox: ${response.status}`);
  }

  return response.json();
}

export async function fetchArchivedMessages(
  signal?: AbortSignal,
): Promise<InboxMessage[]> {
  const url = new URL("/api/v1/ingestion/inbox", BACKEND_URL);
  url.searchParams.set("archived", "true");

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to load archived messages: ${response.status}`);
  }

  return response.json();
}

export async function fetchInboxPage(
  limit = 100,
  cursor?: string | null,
  signal?: AbortSignal,
): Promise<InboxPageResponse> {
  const url = new URL("/api/v1/ingestion/inbox/page", BACKEND_URL);
  url.searchParams.set("limit", String(limit));
  if (cursor) {
    url.searchParams.set("cursor", cursor);
  }

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to load inbox page: ${response.status}`);
  }

  return response.json();
}

export async function fetchConnectors(
  signal?: AbortSignal,
): Promise<ConnectorStatus[]> {
  const url = new URL("/api/v1/ingestion/connectors", BACKEND_URL);

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to load connectors: ${response.status}`);
  }

  return response.json();
}

export async function fetchConnectorRuns(
  limit = 12,
  signal?: AbortSignal,
): Promise<ConnectorRun[]> {
  const url = new URL("/api/v1/ingestion/connectors/runs", BACKEND_URL);
  url.searchParams.set("limit", String(limit));

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to load connector runs: ${response.status}`);
  }

  return response.json();
}

export async function fetchAudit(
  limit = 100,
  signal?: AbortSignal,
): Promise<AuditLogEntry[]> {
  const url = new URL("/api/v1/ingestion/audit", BACKEND_URL);
  url.searchParams.set("limit", String(limit));

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to load audit log: ${response.status}`);
  }

  return response.json();
}

export async function fetchConnectorCapabilities(
  signal?: AbortSignal,
): Promise<ConnectorCapability[]> {
  const url = new URL("/api/v1/ingestion/connectors/capabilities", BACKEND_URL);

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    throw new Error(
      `Failed to load connector capabilities: ${response.status}`,
    );
  }

  return response.json();
}

export async function syncConnector(
  sourceType: string,
  signal?: AbortSignal,
): Promise<{ tenant_id: string; processed: number; inserted: number; duplicates: number; rejected: number }> {
  const url = new URL(`/api/v1/ingestion/connectors/${encodeURIComponent(sourceType)}/sync`, BACKEND_URL);

  const response = await fetch(url.toString(), {
    method: "POST",
    cache: "no-store",
    signal,
    headers: baseHeaders({ "Content-Type": "application/json" }),
    body: "{}",
  });

  if (!response.ok) {
    return parseErrorDetail(response, `Failed to sync ${sourceType}`);
  }

  return response.json();
}

export async function sendReply(
  eventId: string,
  text: string,
  signal?: AbortSignal,
): Promise<ReplyResponse> {
  const url = new URL(
    `/api/v1/ingestion/messages/${encodeURIComponent(eventId)}/reply`,
    BACKEND_URL,
  );

  const response = await fetch(url.toString(), {
    method: "POST",
    cache: "no-store",
    signal,
    headers: baseHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Failed to send reply: ${response.status}`);
  }

  return response.json();
}

export async function fetchMessageAttachment(
  eventId: string,
  signal?: AbortSignal,
): Promise<string> {
  const url = new URL(
    `/api/v1/ingestion/messages/${encodeURIComponent(eventId)}/attachment`,
    BACKEND_URL,
  );

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Failed to load attachment: ${response.status}`);
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

export async function archiveMessage(
  eventId: string,
  signal?: AbortSignal,
): Promise<{ status: string; event_id: string }> {
  const url = new URL(
    `/api/v1/ingestion/messages/${encodeURIComponent(eventId)}/archive`,
    BACKEND_URL,
  );

  const response = await fetch(url.toString(), {
    method: "POST",
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Failed to archive message: ${response.status}`);
  }

  return response.json();
}

export async function unarchiveMessage(
  eventId: string,
  signal?: AbortSignal,
): Promise<{ status: string; event_id: string }> {
  const url = new URL(
    `/api/v1/ingestion/messages/${encodeURIComponent(eventId)}/unarchive`,
    BACKEND_URL,
  );

  const response = await fetch(url.toString(), {
    method: "POST",
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Failed to unarchive message: ${response.status}`);
  }

  return response.json();
}

export async function snoozeMessage(
  eventId: string,
  hours?: number,
  signal?: AbortSignal,
): Promise<{ status: string; event_id: string; snoozed_until: string }> {
  const url = new URL(
    `/api/v1/ingestion/messages/${encodeURIComponent(eventId)}/snooze`,
    BACKEND_URL,
  );

  const response = await fetch(url.toString(), {
    method: "POST",
    cache: "no-store",
    signal,
    headers: baseHeaders({ "Content-Type": "application/json" }),
    body: hours !== undefined ? JSON.stringify({ hours }) : undefined,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Failed to snooze message: ${response.status}`);
  }

  return response.json();
}

async function parseErrorDetail(response: Response, fallback: string): Promise<never> {
  const body = await response.json().catch(() => null);
  throw new Error(body?.detail || `${fallback}: ${response.status}`);
}

export async function fetchGenericConnectors(
  signal?: AbortSignal,
): Promise<GenericConnectorConfig[]> {
  const url = new URL("/api/v1/ingestion/connectors/generic", BACKEND_URL);

  const response = await fetch(url.toString(), {
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    return parseErrorDetail(response, "Failed to load generic connectors");
  }

  return response.json();
}

export async function createGenericConnector(
  payload: GenericConnectorCreateInput,
  signal?: AbortSignal,
): Promise<GenericConnectorConfig> {
  const url = new URL("/api/v1/ingestion/connectors/generic", BACKEND_URL);

  const response = await fetch(url.toString(), {
    method: "POST",
    cache: "no-store",
    signal,
    headers: baseHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    return parseErrorDetail(response, "Failed to create generic connector");
  }

  return response.json();
}

export async function updateGenericConnector(
  configId: string,
  payload: GenericConnectorUpdateInput,
  signal?: AbortSignal,
): Promise<GenericConnectorConfig> {
  const url = new URL(
    `/api/v1/ingestion/connectors/generic/${encodeURIComponent(configId)}`,
    BACKEND_URL,
  );

  const response = await fetch(url.toString(), {
    method: "PATCH",
    cache: "no-store",
    signal,
    headers: baseHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    return parseErrorDetail(response, "Failed to update generic connector");
  }

  return response.json();
}

export async function deleteGenericConnector(
  configId: string,
  signal?: AbortSignal,
): Promise<void> {
  const url = new URL(
    `/api/v1/ingestion/connectors/generic/${encodeURIComponent(configId)}`,
    BACKEND_URL,
  );

  const response = await fetch(url.toString(), {
    method: "DELETE",
    cache: "no-store",
    signal,
    headers: baseHeaders(),
  });

  if (!response.ok) {
    return parseErrorDetail(response, "Failed to delete generic connector");
  }
}

export async function deleteAllTenantMessages(
  confirmTenantId: string,
  totpCode: string,
  signal?: AbortSignal,
): Promise<{ status: string; deleted_count: number }> {
  const url = new URL("/api/v1/admin/tenant/messages/delete", BACKEND_URL);

  const response = await fetch(url.toString(), {
    method: "POST",
    cache: "no-store",
    signal,
    headers: baseHeaders({ "Content-Type": "application/json", "X-TOTP-Code": totpCode }),
    body: JSON.stringify({ confirm_tenant_id: confirmTenantId }),
  });

  if (!response.ok) {
    return parseErrorDetail(response, "Failed to delete tenant messages");
  }

  return response.json();
}

export async function rotateApiKeyCandidate(
  totpCode: string,
  signal?: AbortSignal,
): Promise<{ candidate_api_key: string; instructions: string }> {
  const url = new URL("/api/v1/admin/api-key/rotate", BACKEND_URL);

  const response = await fetch(url.toString(), {
    method: "POST",
    cache: "no-store",
    signal,
    headers: baseHeaders({ "X-TOTP-Code": totpCode }),
  });

  if (!response.ok) {
    return parseErrorDetail(response, "Failed to generate a candidate API key");
  }

  return response.json();
}

export async function exportTenantAudit(
  totpCode: string,
  signal?: AbortSignal,
): Promise<{ tenant_id: string; exported_count: number; entries: AuditLogEntry[] }> {
  const url = new URL("/api/v1/admin/tenant/audit/export", BACKEND_URL);

  const response = await fetch(url.toString(), {
    method: "GET",
    cache: "no-store",
    signal,
    headers: baseHeaders({ "X-TOTP-Code": totpCode }),
  });

  if (!response.ok) {
    return parseErrorDetail(response, "Failed to export audit log");
  }

  return response.json();
}
