"use client"

import type { ReactNode } from "react"
import { ConnectorCapability, ConnectorRun, ConnectorStatus, Mode } from "../lib/types"
import {
	AlertIcon,
	InboxIcon,
	LockIcon,
	SettingsIcon,
	ShieldIcon,
	StarIcon,
} from "./Icons"

type Props = {
	activeMode: Mode
	onModeChange: (mode: Mode) => void
	connectorCapabilities?: ConnectorCapability[]
	connectors?: ConnectorStatus[]
	connectorRuns?: ConnectorRun[]
	connectorsRefreshing?: boolean
	connectorsLastUpdatedAt?: string | null
	connectorsFailures?: number
	onRefreshConnectors?: () => void
	width?: number
}

const NAV_ITEMS: { id: Mode; label: string; icon: ReactNode }[] = [
	{ id: "normal",   label: "Inbox",           icon: <InboxIcon size={15} /> },
	{ id: "focus",    label: "Focus Mode",       icon: <StarIcon size={15} /> },
	{ id: "incident", label: "Incident",         icon: <AlertIcon size={15} /> },
	{ id: "security", label: "Security Center",  icon: <ShieldIcon size={15} /> },
	{ id: "settings", label: "Settings",         icon: <SettingsIcon size={15} /> },
]

const SOURCE_STYLE: Record<string, { color: string; bg: string; label: string }> = {
	github: { color: "var(--src-email)", bg: "var(--src-email-soft)", label: "GitHub" },
	gitlab: { color: "var(--src-telegram)", bg: "var(--src-telegram-soft)", label: "GitLab" },
	jira: { color: "var(--accent)", bg: "var(--accent-soft)", label: "Jira" },
	linear: { color: "var(--src-slack)", bg: "var(--src-slack-soft)", label: "Linear" },
	telegram: { color: "var(--src-telegram)", bg: "var(--src-telegram-soft)", label: "Telegram" },
	slack: { color: "var(--src-slack)", bg: "var(--src-slack-soft)", label: "Slack" },
	discord: { color: "var(--accent)", bg: "var(--accent-soft)", label: "Discord" },
	zoom: { color: "var(--danger)", bg: "var(--danger-soft)", label: "Zoom" },
	teams: { color: "var(--text-2)", bg: "var(--surface-3)", label: "Teams" },
	google_calendar: { color: "var(--src-email)", bg: "var(--src-email-soft)", label: "Google Calendar" },
	rocketchat: { color: "var(--src-slack)", bg: "var(--src-slack-soft)", label: "Rocket.Chat" },
}

function sourceVisual(sourceType: string): { color: string; bg: string; label: string } {
	const key = sourceType.toLowerCase()
	const found = SOURCE_STYLE[key]
	if (found) return found
	return {
		color: "var(--text-2)",
		bg: "var(--surface-3)",
		label: sourceType.charAt(0).toUpperCase() + sourceType.slice(1),
	}
}

export function Sidebar({
	activeMode,
	onModeChange,
	connectorCapabilities = [],
	connectors = [],
	connectorRuns = [],
	connectorsRefreshing = false,
	connectorsLastUpdatedAt = null,
	connectorsFailures = 0,
	onRefreshConnectors,
	width = 218,
}: Props) {
	function getConnector(sourceId: string): ConnectorStatus | undefined {
		return connectors.find((c) => c.source_type.toLowerCase() === sourceId.toLowerCase())
	}

	function getStatus(sourceId: string): string {
		const match = getConnector(sourceId)
		return match?.status ?? "unknown"
	}

	function statusColor(status: string): string {
		switch (status) {
			case "healthy":
				return "var(--success)"
			case "degraded":
				return "var(--warning)"
			case "error":
				return "var(--danger)"
			default:
				return "var(--text-3)"
		}
	}

	function formatUpdatedAt(value: string | null): string {
		if (!value) return "Never"
		const d = new Date(value)
		if (Number.isNaN(d.getTime())) return "Unknown"
		return d.toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
	}

	function formatSyncAt(value: string | null): string {
		if (!value) return "sync: n/a"
		const d = new Date(value)
		if (Number.isNaN(d.getTime())) return "sync: ?"
		return `sync: ${d.toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit" })}`
	}

	function formatRunAt(value: string): string {
		const d = new Date(value)
		if (Number.isNaN(d.getTime())) return "--:--"
		return d.toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
	}

	const visibleSources = connectorCapabilities
		.filter((c) => c.available && c.sync_supported)
		.map((c) => ({ id: c.source_type, configured: c.configured, ...sourceVisual(c.source_type) }))

	return (
		<aside
			style={{
				width,
				minWidth: width,
				height: "100vh",
				borderRight: "1px solid var(--border)",
				padding: "16px 12px",
				display: "flex",
				flexDirection: "column",
				background: "var(--surface)",
				fontFamily: "var(--font-ui)",
				overflowY: "auto",
			}}
		>
			{/* Logo */}
			<div
				style={{
					fontSize: 15,
					fontWeight: "var(--head-weight)",
					letterSpacing: "var(--head-tracking)",
					color: "var(--text)",
					padding: "4px 10px 20px",
					fontFamily: "var(--font-head)",
				}}
			>
				ALLinO
			</div>

			{/* Primary nav */}
			<nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
				{NAV_ITEMS.map((item) => (
					<button
						key={item.id}
						className={`nav-item${item.id === activeMode ? " active" : ""}`}
						onClick={() => onModeChange(item.id)}
						aria-current={item.id === activeMode ? "page" : undefined}
					>
						{item.icon}
						<span>{item.label}</span>
					</button>
				))}
			</nav>

			{/* Sources */}
			<div style={{ marginTop: 24 }}>
				<div
					style={{
						display: "flex",
						alignItems: "center",
						gap: 8,
						padding: "0 10px 6px",
					}}
				>
					<span
						style={{
							fontSize: 10,
							fontFamily: "var(--font-mono)",
							color: "var(--text-3)",
							letterSpacing: "0.08em",
							textTransform: "uppercase",
						}}
					>
						Sources
					</span>
					<button
						onClick={onRefreshConnectors}
						disabled={connectorsRefreshing}
						aria-label="Refresh sources"
						title="Refresh sources"
						style={{
							marginLeft: "auto",
							display: "inline-flex",
							alignItems: "center",
							justifyContent: "center",
							width: 22,
							height: 22,
							borderRadius: "var(--r-chip)",
							border: "1px solid var(--border)",
							background: "var(--surface-2)",
							color: "var(--text-2)",
							cursor: connectorsRefreshing ? "not-allowed" : "pointer",
							opacity: connectorsRefreshing ? 0.6 : 1,
						}}
					>
						<svg
							width="12"
							height="12"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							strokeWidth="1.8"
							strokeLinecap="round"
							strokeLinejoin="round"
						>
							<polyline points="23 4 23 10 17 10" />
							<polyline points="1 20 1 14 7 14" />
							<path d="M3.51 9a9 9 0 0 1 14.13-3.36L23 10" />
							<path d="M20.49 15a9 9 0 0 1-14.13 3.36L1 14" />
						</svg>
					</button>
				</div>
				<div
					style={{
						padding: "0 10px 8px",
						fontSize: 10,
						fontFamily: "var(--font-mono)",
						color: connectorsFailures > 0 ? "var(--warning)" : "var(--text-3)",
					}}
				>
					{connectorsRefreshing ? "Refreshing..." : `Updated: ${formatUpdatedAt(connectorsLastUpdatedAt)}`}
					{connectorsFailures > 0 ? ` | retries: ${connectorsFailures}` : ""}
				</div>
				{visibleSources.map((src) => (
					(() => {
						const connector = getConnector(src.id)
						return (
					<div
						key={src.id}
						title={connector?.last_error ?? undefined}
						style={{
							display: "flex",
							flexDirection: "column",
							alignItems: "stretch",
							gap: 8,
							padding: "6px 10px",
							borderRadius: "var(--r-btn)",
							color: "var(--text-2)",
							fontSize: 13,
						}}
					>
						<div style={{ display: "flex", alignItems: "center", gap: 8 }}>
							<span
								style={{
									display: "inline-flex",
									alignItems: "center",
									justifyContent: "center",
									width: 16,
									height: 16,
									borderRadius: 4,
									background: src.bg,
									color: src.color,
									fontSize: 9,
									fontFamily: "var(--font-mono)",
									fontWeight: 600,
									flexShrink: 0,
								}}
							>
								{src.id.slice(0, 2).toUpperCase()}
							</span>
							{src.label}
							{!src.configured && (
								<span
									style={{
										fontSize: 9,
										fontFamily: "var(--font-mono)",
										textTransform: "uppercase",
										color: "var(--warning)",
										background: "var(--warning-soft)",
										border: "1px solid var(--warning)",
										borderRadius: "var(--r-chip)",
										padding: "1px 4px",
									}}
								>
									setup
								</span>
							)}
							<span
								style={{
									marginLeft: "auto",
									fontSize: 10,
									fontFamily: "var(--font-mono)",
									color: statusColor(getStatus(src.id)),
									textTransform: "uppercase",
								}}
							>
								{getStatus(src.id)}
							</span>
						</div>
						{connector && (
							<div
								style={{
									fontSize: 10,
									fontFamily: "var(--font-mono)",
									color: connector.last_error ? "var(--warning)" : "var(--text-3)",
									paddingLeft: 24,
								}}
							>
								{`${formatSyncAt(connector.last_synced_at)} | p:${connector.last_processed} i:${connector.last_inserted} r:${connector.last_rejected}`}
								{connector.last_error ? " | error" : ""}
							</div>
						)}
					</div>
						)
					})()
				))}
			</div>

			<div style={{ marginTop: 18 }}>
				<div
					style={{
						padding: "0 10px 6px",
						fontSize: 10,
						fontFamily: "var(--font-mono)",
						color: "var(--text-3)",
						letterSpacing: "0.08em",
						textTransform: "uppercase",
					}}
				>
					Recent Runs
				</div>
				{connectorRuns.length === 0 ? (
					<div
						style={{
							padding: "4px 10px",
							fontSize: 10,
							fontFamily: "var(--font-mono)",
							color: "var(--text-3)",
						}}
					>
						No runs yet
					</div>
				) : (
					connectorRuns.slice(0, 8).map((run) => (
						<div
							key={run.id}
							title={run.error ?? undefined}
							style={{
								display: "flex",
								flexDirection: "column",
								gap: 3,
								padding: "6px 10px",
								borderRadius: "var(--r-btn)",
								border: "1px solid var(--border)",
								marginBottom: 6,
								background: "var(--surface-2)",
							}}
						>
							<div
								style={{
									display: "flex",
									alignItems: "center",
									gap: 8,
									fontSize: 10,
									fontFamily: "var(--font-mono)",
									textTransform: "uppercase",
								}}
							>
								<span style={{ color: "var(--text-2)" }}>{run.source_type}</span>
								<span style={{ color: statusColor(run.status), marginLeft: "auto" }}>{run.status}</span>
								<span style={{ color: "var(--text-3)" }}>{formatRunAt(run.synced_at)}</span>
							</div>
							<div
								style={{
									fontSize: 10,
									fontFamily: "var(--font-mono)",
									color: run.error ? "var(--warning)" : "var(--text-3)",
								}}
							>
								{`p:${run.processed} i:${run.inserted} d:${run.duplicates} r:${run.rejected}`}
								{run.error ? " | error" : ""}
							</div>
						</div>
					))
				)}
			</div>

			{/* Spacer */}
			<div style={{ flex: 1 }} />

			{/* Account chip */}
			<div
				style={{
					display: "flex",
					alignItems: "center",
					gap: 8,
					padding: "8px 10px",
					border: "1px solid var(--border)",
					borderRadius: "var(--r-btn)",
					color: "var(--success)",
					fontSize: 12,
					fontFamily: "var(--font-mono)",
					background: "var(--success-soft)",
				}}
			>
				<LockIcon size={13} />
				Encrypted
			</div>
		</aside>
	)
}
