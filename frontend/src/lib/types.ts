export type Mode = "normal" | "focus" | "incident" | "security" | "settings";

export type Priority = "high" | "medium" | "normal";

export type InboxMessage = {
  event_id: string;
  tenant_id: string;
  source: string;
  external_id: string;
  timestamp: string;
  preview: string;
  thread_key: string;
  priority: Priority;
  // For rocketchat: the id of the thread-root message this one replies within
  // (see backend normalizer's _reply_target) -- for github/gitlab this same
  // field instead holds a comment-target URL, a different, source-specific
  // meaning re-using the same underlying DB column.
  reply_target?: string | null;
  attachment_ref?: string | null;
  attachment_type?: "image" | "video" | "file" | null;
  attachment_name?: string | null;
  attachment_size?: number | null;
  channel_kind?: "team" | "channel" | "dm" | null;
  channel_team?: string | null;
};

export type ChannelKind = "team" | "channel" | "dm";

export type ChannelSummary = {
  thread_key: string;
  source: string;
  channel_kind: ChannelKind | null;
  channel_team: string | null;
  latest: InboxMessage;
  unread: boolean;
};

// Sources whose messages carry channel_kind -- only these switch the Inbox into
// channel-browser mode (grouped by channel/DM/team) instead of the flat,
// one-row-per-message view used by every other source.
export const CHAT_SHAPED_SOURCES = ["rocketchat", "telegram"] as const;

export type InboxPageResponse = {
  items: InboxMessage[];
  next_cursor: string | null;
};

export type DigestResponse = {
  tenant_id: string;
  since_hours: number;
  total: number;
  by_source: Record<string, number>;
  by_priority: Record<string, number>;
  highlights: InboxMessage[];
};

export type ConnectorStatus = {
  id: string;
  tenant_id: string;
  source_type: string;
  status: "starting" | "healthy" | "stopped" | "degraded" | "error" | string;
  created_at: string;
  updated_at: string | null;
  last_synced_at: string | null;
  last_error: string | null;
  last_processed: number;
  last_inserted: number;
  last_duplicates: number;
  last_rejected: number;
};

export type ConnectorRun = {
  id: number;
  tenant_id: string;
  source_type: string;
  status: "starting" | "healthy" | "stopped" | "degraded" | "error" | string;
  synced_at: string;
  processed: number;
  inserted: number;
  duplicates: number;
  rejected: number;
  error: string | null;
  created_at: string;
};

export type ConnectorCapability = {
  source_type: string;
  available: boolean;
  configured: boolean;
  requires_secret: boolean;
  sync_supported: boolean;
};

export type AuditLogEntry = {
  id: number;
  tenant_id: string;
  action: string;
  actor: string | null;
  metadata: string | null;
  created_at: string;
};

export const REPLY_SUPPORTED_SOURCES = [
  "telegram",
  "slack",
  "discord",
  "rocketchat",
  "github",
  "gitlab",
  "jira",
  "linear",
] as const;

export type ReplyResponse = {
  status: string;
  event_id: string;
  source: string;
};

export type GenericConnectorAuthMethod = "none" | "api_key" | "bearer" | "basic";

export type GenericConnectorFieldMapping = {
  externalId: string;
  timestamp: string;
  preview?: string | null;
  items_path?: string | null;
};

export type GenericConnectorConfig = {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  base_url: string | null;
  auth_method: GenericConnectorAuthMethod;
  auth_header_name: string | null;
  poll_interval_seconds: number | null;
  field_mapping: GenericConnectorFieldMapping;
  webhook_enabled: boolean;
  webhook_url: string | null;
  status: string;
  created_at: string;
  updated_at: string | null;
};

export type GenericConnectorCreateInput = {
  name: string;
  base_url?: string | null;
  auth_method: GenericConnectorAuthMethod;
  auth_header_name?: string | null;
  poll_interval_seconds?: number | null;
  field_mapping: GenericConnectorFieldMapping;
  webhook_enabled: boolean;
};

export type GenericConnectorUpdateInput = {
  base_url?: string | null;
  auth_method?: GenericConnectorAuthMethod;
  auth_header_name?: string | null;
  poll_interval_seconds?: number | null;
  field_mapping?: GenericConnectorFieldMapping;
  webhook_enabled?: boolean;
};

export type BuiltinConnectorSourceType =
  | "github"
  | "gitlab"
  | "jira"
  | "linear"
  | "telegram"
  | "slack"
  | "discord"
  | "zoom"
  | "teams"
  | "rocketchat"
  | "google_calendar";

export type BuiltinConnectorSecretSummary = {
  source_type: BuiltinConnectorSourceType;
  configured: true;
  poll_interval_seconds: number | null;
  status: string;
  created_at: string;
  updated_at: string | null;
};

export type BuiltinConnectorSecretInput = {
  // Optional overall: google_calendar can authenticate via client_id/client_secret/
  // refresh_token instead of a raw token. Every other source still requires it
  // (enforced server-side).
  token?: string | null;
  base_url?: string | null;
  user_id?: string | null;
  channel_id?: string | null;
  calendar_id?: string | null;
  client_id?: string | null;
  client_secret?: string | null;
  refresh_token?: string | null;
  poll_interval_seconds?: number | null;
};

