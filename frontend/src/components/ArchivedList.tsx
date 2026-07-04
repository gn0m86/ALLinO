"use client"

import { useEffect, useRef, useState } from "react"

import { fetchArchivedMessages, unarchiveMessage } from "../lib/api"
import { InboxMessage } from "../lib/types"

type Props = {
	onClose: () => void
}

function formatTime(ts: string): string {
	const d = new Date(ts)
	if (isNaN(d.getTime())) return ""
	const diff = Date.now() - d.getTime()
	const m = Math.floor(diff / 60000)
	if (m < 1) return "now"
	if (m < 60) return `${m}m`
	const h = Math.floor(m / 60)
	if (h < 24) return `${h}h`
	return `${Math.floor(h / 24)}d`
}

export function ArchivedList({ onClose }: Props) {
	const [items, setItems] = useState<InboxMessage[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)
	const [unarchivingId, setUnarchivingId] = useState<string | null>(null)
	const disposedRef = useRef(false)

	const load = () => {
		const controller = new AbortController()
		setLoading(true)
		setError(null)
		fetchArchivedMessages(controller.signal)
			.then((data) => {
				if (disposedRef.current) return
				setItems(data)
			})
			.catch((e: unknown) => {
				if (e instanceof DOMException && e.name === "AbortError") return
				if (disposedRef.current) return
				setError(e instanceof Error ? e.message : "Failed to load archived messages")
			})
			.finally(() => {
				if (!disposedRef.current) setLoading(false)
			})
		return controller
	}

	useEffect(() => {
		disposedRef.current = false
		const controller = load()
		return () => {
			disposedRef.current = true
			controller.abort()
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [])

	async function handleUnarchive(eventId: string) {
		if (unarchivingId) return
		setUnarchivingId(eventId)
		try {
			await unarchiveMessage(eventId)
			setItems((prev) => prev.filter((i) => i.event_id !== eventId))
		} catch (e: unknown) {
			setError(e instanceof Error ? e.message : "Failed to unarchive message")
		} finally {
			setUnarchivingId(null)
		}
	}

	return (
		<div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
			<div
				style={{
					display: "flex",
					alignItems: "center",
					gap: 8,
					padding: "14px 16px",
					borderBottom: "1px solid var(--border)",
					flexShrink: 0,
				}}
			>
				<h2
					style={{
						margin: 0,
						flex: 1,
						fontSize: 15,
						fontWeight: "var(--head-weight)",
						fontFamily: "var(--font-head)",
						letterSpacing: "var(--head-tracking)",
						color: "var(--text)",
					}}
				>
					Archived
				</h2>
				<button
					onClick={onClose}
					style={{
						fontSize: 11,
						fontFamily: "var(--font-mono)",
						color: "var(--accent)",
						background: "transparent",
						border: "1px solid var(--border)",
						borderRadius: "var(--r-btn)",
						padding: "4px 8px",
						cursor: "pointer",
					}}
				>
					Back to Inbox
				</button>
			</div>

			<div style={{ flex: 1, overflowY: "auto" }}>
				{loading && (
					<div
						style={{
							padding: "32px 16px",
							textAlign: "center",
							color: "var(--text-3)",
							fontSize: 13,
							fontFamily: "var(--font-mono)",
						}}
					>
						Loading archived messages…
					</div>
				)}

				{!loading && error && (
					<div
						style={{
							margin: 12,
							display: "flex",
							alignItems: "center",
							gap: 10,
							fontSize: 12,
							color: "var(--danger)",
							background: "var(--danger-soft)",
							borderRadius: "var(--r-card)",
							padding: "8px 10px",
						}}
					>
						<span>Failed to load — {error}</span>
						<button
							onClick={() => load()}
							style={{
								fontSize: 11,
								fontFamily: "var(--font-mono)",
								color: "var(--danger)",
								background: "transparent",
								border: "1px solid var(--border)",
								borderRadius: "var(--r-btn)",
								padding: "4px 8px",
								cursor: "pointer",
								whiteSpace: "nowrap",
							}}
						>
							Retry
						</button>
					</div>
				)}

				{!loading && !error && items.length === 0 && (
					<div
						style={{
							padding: "32px 16px",
							textAlign: "center",
							color: "var(--text-3)",
							fontSize: 13,
							fontFamily: "var(--font-mono)",
						}}
					>
						No archived messages.
					</div>
				)}

				{!loading && !error && items.length > 0 && (
					<ul role="list" style={{ listStyle: "none", margin: 0, padding: "4px 8px" }}>
						{items.map((item) => (
							<li
								key={item.event_id}
								role="listitem"
								style={{
									display: "flex",
									alignItems: "center",
									gap: 10,
									padding: "10px 8px",
									borderBottom: "1px solid var(--border)",
								}}
							>
								<div style={{ flex: 1, minWidth: 0 }}>
									<div
										style={{
											fontSize: 13,
											fontWeight: 500,
											color: "var(--text)",
											whiteSpace: "nowrap",
											overflow: "hidden",
											textOverflow: "ellipsis",
										}}
									>
										{item.external_id}
									</div>
									<div
										style={{
											fontSize: 12,
											color: "var(--text-3)",
											whiteSpace: "nowrap",
											overflow: "hidden",
											textOverflow: "ellipsis",
										}}
									>
										{item.source} · {item.preview?.slice(0, 60) || "(no preview)"} · {formatTime(item.timestamp)}
									</div>
								</div>
								<button
									onClick={() => void handleUnarchive(item.event_id)}
									disabled={unarchivingId === item.event_id}
									aria-label={`Unarchive ${item.external_id}`}
									style={{
										fontSize: 11,
										fontFamily: "var(--font-mono)",
										color: "var(--accent)",
										background: "transparent",
										border: "1px solid var(--border)",
										borderRadius: "var(--r-btn)",
										padding: "4px 8px",
										cursor: unarchivingId === item.event_id ? "default" : "pointer",
										opacity: unarchivingId === item.event_id ? 0.6 : 1,
										flexShrink: 0,
										whiteSpace: "nowrap",
									}}
								>
									{unarchivingId === item.event_id ? "…" : "Unarchive"}
								</button>
							</li>
						))}
					</ul>
				)}
			</div>
		</div>
	)
}
