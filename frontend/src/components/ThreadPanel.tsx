"use client"

import { useEffect, useState } from "react"

import { archiveMessage, describeBackendTransport, getStoredApiKey, snoozeMessage } from "../lib/api"
import { getDisplayPreview, getDisplayTitle } from "../lib/chatPreview"
import { formatClockCluster, formatShort, useTimePrefs } from "../lib/timePrefs"
import { ConnectorRun, ConnectorStatus, InboxMessage } from "../lib/types"
import { AttachmentViewer } from "./AttachmentViewer"
import { ConnectorOpsPanel } from "./ConnectorOpsPanel"
import { AlertIcon, ShieldCheck } from "./Icons"
import { ReplyComposer } from "./ReplyComposer"

type Props = {
	item: InboxMessage | null
	relatedItems?: InboxMessage[]
	connectors?: ConnectorStatus[]
	connectorRuns?: ConnectorRun[]
	connectorsRefreshing?: boolean
	connectorsLastUpdatedAt?: string | null
	onArchived?: (eventId: string) => void
	onSnoozed?: (eventId: string) => void
	onSelectRelated?: (item: InboxMessage) => void
}

const SOURCE_MAP: Record<string, { color: string; bg: string; label: string }> = {
	github:   { color: "var(--src-email)",    bg: "var(--src-email-soft)",    label: "GitHub" },
	gitlab:   { color: "var(--src-telegram)", bg: "var(--src-telegram-soft)", label: "GitLab" },
	jira:     { color: "var(--accent)",       bg: "var(--accent-soft)",       label: "Jira" },
	linear:   { color: "var(--src-slack)",    bg: "var(--src-slack-soft)",    label: "Linear" },
	slack:    { color: "var(--src-slack)",    bg: "var(--src-slack-soft)",    label: "Slack"  },
	telegram: { color: "var(--src-telegram)", bg: "var(--src-telegram-soft)", label: "Telegram" },
	email:    { color: "var(--src-email)",    bg: "var(--src-email-soft)",    label: "Email"  },
}
const DEFAULT_SOURCE = { color: "var(--text-3)", bg: "var(--surface-3)", label: "Unknown" }

function getSource(source: string) {
	return SOURCE_MAP[source.toLowerCase()] ?? { ...DEFAULT_SOURCE, label: source }
}

type SnoozeOption = { label: string; hours: number }

function hoursUntil(target: Date): number {
	const ms = target.getTime() - Date.now()
	return Math.max(ms / (1000 * 60 * 60), 0.1)
}

function nextDayAt(hour: number): Date {
	const d = new Date()
	d.setDate(d.getDate() + 1)
	d.setHours(hour, 0, 0, 0)
	return d
}

function snoozeOptions(): SnoozeOption[] {
	return [
		{ label: "1 hour", hours: 1 },
		{ label: "4 hours", hours: 4 },
		{ label: "Tomorrow, 9 AM", hours: hoursUntil(nextDayAt(9)) },
		{ label: "Next week", hours: 24 * 7 },
	]
}

function getInitials(externalId: string): string {
	const parts = externalId.replace(/[#@/]/g, "-").split(/[-_]/).filter(Boolean)
	if (parts.length === 0) return "?"
	if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
	return (parts[0][0] + parts[1][0]).toUpperCase()
}

function SecurityCard({ source }: { source: string }) {
	const src = getSource(source)
	const transport = describeBackendTransport()
	// Only rendered client-side (needs a selected message), so reading
	// localStorage here can't cause a hydration mismatch.
	const identity = getStoredApiKey() ? "API key verified" : "No API key (dev mode)"
	return (
		<div
			style={{
				border: "1px solid var(--border)",
				borderRadius: "var(--r-card)",
				boxShadow: "var(--shadow-1)",
				overflow: "hidden",
				margin: "0 16px 16px",
				fontFamily: "var(--font-ui)",
			}}
		>
			{/* Header */}
			<div
				style={{
					display: "flex",
					alignItems: "center",
					gap: 10,
					padding: "10px 14px",
					borderBottom: "1px solid var(--border)",
				}}
			>
				<div
					style={{
						width: 24,
						height: 24,
						borderRadius: "var(--r-chip)",
						background: transport.secure ? "var(--success-soft)" : "var(--warning-soft)",
						color: transport.secure ? "var(--success)" : "var(--warning)",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						flexShrink: 0,
					}}
				>
					{transport.secure ? <ShieldCheck size={14} /> : <AlertIcon size={14} />}
				</div>
				<span style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text)", flex: 1 }}>
					{transport.secure ? "Conversation secured" : "Connection not encrypted"}
				</span>
				<span
					style={{
						fontSize: 11,
						fontFamily: "var(--font-mono)",
						color: src.color,
						background: src.bg,
						borderRadius: 999,
						padding: "2px 8px",
					}}
				>
					{src.label}
				</span>
			</div>

			{/* Facts grid */}
			<dl
				style={{
					display: "grid",
					gridTemplateColumns: "1fr 1fr",
					margin: 0,
					padding: 0,
				}}
			>
				{[
					{ label: "Transport",  value: transport.label },
					{ label: "Identity",   value: identity },
					{ label: "Content",    value: "Remote media blocked" },
					{ label: "Retention",  value: "Local store only" },
				].map((fact, i) => (
					<div
						key={fact.label}
						style={{
							padding: "10px 14px",
							borderTop: "1px solid var(--border)",
							borderRight: i % 2 === 0 ? "1px solid var(--border)" : undefined,
						}}
					>
						<dt
							style={{
								fontSize: 10,
								fontFamily: "var(--font-mono)",
								textTransform: "uppercase",
								letterSpacing: "0.06em",
								color: "var(--text-3)",
								marginBottom: 3,
							}}
						>
							{fact.label}
						</dt>
						<dd
							style={{
								margin: 0,
								fontSize: 12.5,
								color: "var(--text)",
							}}
						>
							{fact.value}
						</dd>
					</div>
				))}
			</dl>

			{/* Footer */}
			<div
				style={{
					padding: "8px 14px",
					borderTop: "1px solid var(--border)",
					fontSize: 11.5,
					color: "var(--text-3)",
					background: "var(--surface-2)",
				}}
			>
				Previews stay on your device. No read receipts are sent.
			</div>
		</div>
	)
}

export function ThreadPanel({
	item,
	relatedItems = [],
	connectors = [],
	connectorRuns = [],
	connectorsRefreshing = false,
	connectorsLastUpdatedAt = null,
	onArchived,
	onSnoozed,
	onSelectRelated,
}: Props) {
	const [actionPending, setActionPending] = useState<"archive" | "snooze" | null>(null)
	const [actionError, setActionError] = useState<string | null>(null)
	const [snoozeMenuOpen, setSnoozeMenuOpen] = useState(false)
	const timePrefs = useTimePrefs()

	useEffect(() => {
		setActionPending(null)
		setActionError(null)
		setSnoozeMenuOpen(false)
	}, [item?.event_id])

	async function handleArchive() {
		if (!item || actionPending) return
		setActionPending("archive")
		setActionError(null)
		try {
			await archiveMessage(item.event_id)
			onArchived?.(item.event_id)
		} catch (e: unknown) {
			setActionError(e instanceof Error ? e.message : "Failed to archive message")
			setActionPending(null)
		}
	}

	async function handleSnooze(hours: number) {
		if (!item || actionPending) return
		setSnoozeMenuOpen(false)
		setActionPending("snooze")
		setActionError(null)
		try {
			await snoozeMessage(item.event_id, hours)
			onSnoozed?.(item.event_id)
		} catch (e: unknown) {
			setActionError(e instanceof Error ? e.message : "Failed to snooze message")
			setActionPending(null)
		}
	}

	if (!item) {
		return (
			<div
				style={{
					flex: 1,
					display: "flex",
					flexDirection: "column",
					background: "var(--bg)",
					overflowY: "auto",
				}}
			>
				<ConnectorOpsPanel
					connectors={connectors}
					runs={connectorRuns}
					refreshing={connectorsRefreshing}
					lastUpdatedAt={connectorsLastUpdatedAt}
				/>
				<div
					style={{
						flex: 1,
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						color: "var(--text-3)",
						fontSize: 13,
						fontFamily: "var(--font-ui)",
						padding: "12px",
					}}
				>
					Select a message to open thread
				</div>
			</div>
		)
	}

	const src = getSource(item.source)
	const displayTitle = getDisplayTitle(item)
	const initials = getInitials(displayTitle)

	return (
		<div
			style={{
				flex: 1,
				minWidth: 0,
				display: "flex",
				flexDirection: "column",
				height: "100%",
				background: "var(--bg)",
				fontFamily: "var(--font-ui)",
				overflow: "hidden",
			}}
		>
			{/* Sticky header */}
			<div
				style={{
					display: "flex",
					alignItems: "center",
					gap: 12,
					padding: "12px 16px",
					borderBottom: "1px solid var(--border)",
					background: "var(--surface)",
					flexShrink: 0,
				}}
			>
				<div
					style={{
						width: 32,
						height: 32,
						borderRadius: "var(--r-card)",
						background: src.bg,
						color: src.color,
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						fontSize: 12,
						fontFamily: "var(--font-mono)",
						fontWeight: 600,
						flexShrink: 0,
					}}
				>
					{src.label.slice(0, 2).toUpperCase()}
				</div>
				<div style={{ flex: 1, minWidth: 0 }}>
					<div
						style={{
							fontSize: 16.5,
							fontWeight: 600,
							fontFamily: "var(--font-head)",
							letterSpacing: "var(--head-tracking)",
							color: "var(--text)",
							whiteSpace: "nowrap",
							overflow: "hidden",
							textOverflow: "ellipsis",
						}}
					>
						{displayTitle}
					</div>
					<div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 1 }}>
						{src.label} · {formatClockCluster(item.timestamp, timePrefs)}
					</div>
				</div>
				<div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
					<button
						onClick={() => void handleArchive()}
						disabled={actionPending !== null}
						className="icon-btn"
						aria-label="Archive"
						title="Archive"
						style={{ opacity: actionPending !== null ? 0.6 : 1, cursor: actionPending !== null ? "default" : "pointer" }}
					>
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
							<polyline points="21 8 21 21 3 21 3 8" /><rect x="1" y="3" width="22" height="5" /><line x1="10" y1="12" x2="14" y2="12" />
						</svg>
					</button>
					<div style={{ position: "relative" }}>
						<button
							onClick={() => setSnoozeMenuOpen((open) => !open)}
							disabled={actionPending !== null}
							className="icon-btn"
							aria-label="Snooze"
							title="Snooze"
							aria-haspopup="true"
							aria-expanded={snoozeMenuOpen}
							style={{ opacity: actionPending !== null ? 0.6 : 1, cursor: actionPending !== null ? "default" : "pointer" }}
						>
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
								<circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
							</svg>
						</button>
						{snoozeMenuOpen && (
							<>
								<div
									onClick={() => setSnoozeMenuOpen(false)}
									style={{ position: "fixed", inset: 0, zIndex: 10 }}
								/>
								<div
									role="menu"
									aria-label="Snooze duration"
									style={{
										position: "absolute",
										top: "calc(100% + 6px)",
										right: 0,
										zIndex: 11,
										minWidth: 160,
										border: "1px solid var(--border)",
										borderRadius: "var(--r-card)",
										background: "var(--surface)",
										boxShadow: "var(--shadow-1)",
										padding: 4,
										display: "flex",
										flexDirection: "column",
									}}
								>
									{snoozeOptions().map((opt) => (
										<button
											key={opt.label}
											role="menuitem"
											className="menu-item"
											onClick={() => void handleSnooze(opt.hours)}
											style={{
												textAlign: "left",
												padding: "6px 10px",
												border: "none",
												background: "transparent",
												borderRadius: "var(--r-btn)",
												fontSize: 12,
												fontFamily: "var(--font-ui)",
												color: "var(--text)",
												cursor: "pointer",
											}}
										>
											{opt.label}
										</button>
									))}
								</div>
							</>
						)}
					</div>
				</div>
			</div>

			{actionError && (
				<div
					style={{
						margin: "10px 16px 0",
						padding: "8px 12px",
						background: "var(--danger-soft)",
						color: "var(--danger)",
						borderRadius: "var(--r-card)",
						fontSize: 12,
						flexShrink: 0,
					}}
				>
					{actionError}
				</div>
			)}

			{/* Scrollable stream */}
			<div style={{ flex: 1, overflowY: "auto" }}>
				<div style={{ padding: "16px 0 0" }}>
					<SecurityCard source={item.source} />
				</div>

				{/* Message */}
				<div style={{ padding: "0 16px 16px", display: "flex", gap: 12, alignItems: "flex-start" }}>
					<div
						style={{
							width: 32,
							height: 32,
							borderRadius: "50%",
							background: "var(--surface-3)",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							fontSize: 12,
							fontWeight: 600,
							color: "var(--text-2)",
							flexShrink: 0,
						}}
					>
						{initials}
					</div>
					<div style={{ flex: 1, minWidth: 0 }}>
						<div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 6 }}>
							<span style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text)" }}>
								{displayTitle}
							</span>
							<span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
								{formatClockCluster(item.timestamp, timePrefs)}
							</span>
						</div>
						<p
							style={{
								margin: 0,
								fontSize: 14,
								lineHeight: 1.55,
								color: "var(--text-2)",
								maxWidth: "62ch",
							}}
						>
							{getDisplayPreview(item) || "(no preview)"}
						</p>
						{item.attachment_ref && item.attachment_type && (
							<AttachmentViewer eventId={item.event_id} attachmentType={item.attachment_type} attachmentName={item.attachment_name} attachmentSize={item.attachment_size} />
						)}
					</div>
				</div>

				{/* Related events from same source */}
				{relatedItems.length > 0 && (
					<div style={{ padding: "0 16px 16px" }}>
						<div
							style={{
								fontSize: 10,
								fontFamily: "var(--font-mono)",
								color: "var(--text-3)",
								textTransform: "uppercase",
								letterSpacing: "0.08em",
								marginBottom: 8,
							}}
						>
							{relatedItems.length} more from {item!.source}
							{onSelectRelated && " · click any message to open it here"}
						</div>
						<div
							style={{
								border: "1px solid var(--border)",
								borderRadius: "var(--r-card)",
								overflow: "hidden",
								maxHeight: 320,
								overflowY: "auto",
							}}
						>
							{relatedItems.map((rel, i) => {
								const clickable = Boolean(onSelectRelated)
								const Wrapper = clickable ? "button" : "div"
								return (
									<Wrapper
										key={rel.event_id}
										{...(clickable ? { onClick: () => onSelectRelated!(rel), type: "button" as const } : {})}
										style={{
											width: "100%",
											padding: "8px 12px",
											borderTop: i > 0 ? "1px solid var(--border)" : undefined,
											borderLeft: "none",
											borderRight: "none",
											borderBottom: "none",
											display: "flex",
											alignItems: "flex-start",
											gap: 10,
											background: "transparent",
											textAlign: "left",
											cursor: clickable ? "pointer" : "default",
											font: "inherit",
											color: "inherit",
										}}
									>
										<div
											style={{
												fontSize: 10,
												fontFamily: "var(--font-mono)",
												color: "var(--text-3)",
												flexShrink: 0,
												paddingTop: 2,
											}}
										>
											{formatShort(rel.timestamp, timePrefs)}
										</div>
										<div style={{ flex: 1, minWidth: 0 }}>
											<div
												style={{
													fontSize: 12,
													fontWeight: 500,
													color: "var(--text-2)",
													whiteSpace: "nowrap",
													overflow: "hidden",
													textOverflow: "ellipsis",
												}}
											>
												{getDisplayTitle(rel)}
											</div>
											{getDisplayPreview(rel) && (
												<div
													style={{
														fontSize: 12,
														color: "var(--text-3)",
														whiteSpace: "nowrap",
														overflow: "hidden",
														textOverflow: "ellipsis",
														marginTop: 1,
													}}
												>
													{getDisplayPreview(rel)}
												</div>
											)}
										</div>
										{rel.priority !== "normal" && (
											<span
												style={{
													fontSize: 9,
													fontFamily: "var(--font-mono)",
													fontWeight: 700,
													color: rel.priority === "high" ? "var(--danger)" : "var(--warning)",
													flexShrink: 0,
												}}
											>
												{rel.priority.toUpperCase()}
											</span>
										)}
									</Wrapper>
								)
							})}
						</div>
					</div>
				)}
			</div>

			{/* Sticky composer */}
			<ReplyComposer item={item} sourceLabel={src.label} />
		</div>
	)
}
