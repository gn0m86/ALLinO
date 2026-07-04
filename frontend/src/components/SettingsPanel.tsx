"use client"

import { useState } from "react"

import { RUNTIME_CONFIG, syncConnector } from "../lib/api"
import { formatShort, useTimePrefs } from "../lib/timePrefs"
import { ConnectorCapability, ConnectorStatus } from "../lib/types"
import { AdminAuditExport } from "./AdminAuditExport"
import { ApiKeyRotatePanel } from "./ApiKeyRotatePanel"
import { ApiKeySettings } from "./ApiKeySettings"
import { DangerZone } from "./DangerZone"
import { BuiltinConnectorSecretsPanel } from "./BuiltinConnectorSecretsPanel"
import { GenericConnectorsPanel } from "./GenericConnectorsPanel"
import { TimeDisplaySettings } from "./TimeDisplaySettings"

type Props = {
	capabilities?: ConnectorCapability[]
	connectors?: ConnectorStatus[]
}

function rowLabel(cap: ConnectorCapability): string {
	if (!cap.available) return "not yet available"
	if (!cap.configured) return cap.requires_secret ? "needs a secret configured" : "not configured"
	return cap.sync_supported ? "ready" : "available, sync pending"
}

function rowColor(cap: ConnectorCapability): string {
	if (!cap.available) return "var(--text-3)"
	if (!cap.configured) return "var(--warning)"
	return "var(--success)"
}

function ConnectedSourceRow({ cap, connector }: { cap: ConnectorCapability; connector?: ConnectorStatus }) {
	const [pending, setPending] = useState(false)
	const [message, setMessage] = useState<string | null>(null)
	// Overrides connector.last_synced_at right after a manual sync, for instant
	// feedback -- the connectors list only refreshes on its own ~15s poll cycle
	// (see page.tsx), and that prop update naturally takes over once it lands.
	const [optimisticSyncedAt, setOptimisticSyncedAt] = useState<string | null>(null)
	const lastSyncedAt = optimisticSyncedAt ?? connector?.last_synced_at ?? null
	const timePrefs = useTimePrefs()

	async function handleSync() {
		setPending(true)
		setMessage(null)
		try {
			const result = await syncConnector(cap.source_type)
			setMessage(`Synced — ${result.inserted} new`)
			setOptimisticSyncedAt(new Date().toISOString())
		} catch (e: unknown) {
			setMessage(e instanceof Error ? e.message : "Sync failed")
		} finally {
			setPending(false)
		}
	}

	const canSync = cap.available && cap.configured && cap.sync_supported

	return (
		<div
			style={{
				display: "grid",
				gridTemplateColumns: "1fr auto auto",
				alignItems: "center",
				gap: 8,
				padding: "6px 0",
				borderTop: "1px solid var(--border)",
				fontSize: 12,
			}}
		>
			<span style={{ color: "var(--text-2)", textTransform: "capitalize" }}>{cap.source_type}</span>
			<span style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 1 }}>
				<span style={{ color: rowColor(cap), fontFamily: "var(--font-mono)", fontSize: 11 }}>
					{message ?? rowLabel(cap)}
				</span>
				{lastSyncedAt && (
					<span style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 10 }}>
						last synced {formatShort(lastSyncedAt, timePrefs)}
					</span>
				)}
			</span>
			{canSync && (
				<button
					onClick={() => void handleSync()}
					disabled={pending}
					style={{
						padding: "3px 10px",
						background: "transparent",
						color: "var(--accent)",
						border: "1px solid var(--border)",
						borderRadius: "var(--r-btn)",
						fontSize: 11,
						fontFamily: "var(--font-mono)",
						cursor: pending ? "default" : "pointer",
						opacity: pending ? 0.5 : 1,
					}}
				>
					{pending ? "Syncing…" : "Sync now"}
				</button>
			)}
		</div>
	)
}

export function SettingsPanel({ capabilities = [], connectors = [] }: Props) {
	return (
		<div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
			<div
				style={{
					padding: "14px 16px",
					borderBottom: "1px solid var(--border)",
					flexShrink: 0,
				}}
			>
				<h2
					style={{
						margin: 0,
						fontSize: 15,
						fontWeight: "var(--head-weight)",
						fontFamily: "var(--font-head)",
						letterSpacing: "var(--head-tracking)",
						color: "var(--text)",
					}}
				>
					Settings
				</h2>
			</div>

			<div style={{ flex: 1, overflowY: "auto", padding: 20 }}>
				<div
					style={{
						border: "1px solid var(--border)",
						borderRadius: "var(--r-card)",
						background: "var(--surface)",
						padding: "14px 16px",
						marginBottom: 16,
					}}
				>
					<div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
						Workspace
					</div>
					<div style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: 6, fontSize: 12 }}>
						<span style={{ color: "var(--text-3)" }}>Tenant</span>
						<span style={{ fontFamily: "var(--font-mono)", color: "var(--text)" }}>{RUNTIME_CONFIG.tenantId}</span>
						<span style={{ color: "var(--text-3)" }}>Backend</span>
						<span style={{ fontFamily: "var(--font-mono)", color: "var(--text)" }}>{RUNTIME_CONFIG.backendUrl}</span>
					</div>
				</div>

				<ApiKeySettings />

				<TimeDisplaySettings />

				<div
					style={{
						border: "1px solid var(--border)",
						borderRadius: "var(--r-card)",
						background: "var(--surface)",
						padding: "14px 16px",
					}}
				>
					<div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
						Connected Sources
					</div>
					{capabilities.length === 0 ? (
						<div style={{ fontSize: 12, color: "var(--text-3)" }}>No connector data yet.</div>
					) : (
						capabilities.map((cap) => (
							<ConnectedSourceRow
								key={cap.source_type}
								cap={cap}
								connector={connectors.find((c) => c.source_type === cap.source_type)}
							/>
						))
					)}
					<div style={{ marginTop: 10, fontSize: 11, color: "var(--text-3)" }}>
						The deployment-wide credential for each source (if any) is configured via
						environment variables (or Vault, if enabled) on the backend. Use "Your Own
						Credentials" below to bring your own token for this tenant instead.
					</div>
				</div>

				<BuiltinConnectorSecretsPanel />

				<GenericConnectorsPanel />

				<AdminAuditExport />

				<ApiKeyRotatePanel />

				<DangerZone />
			</div>
		</div>
	)
}
