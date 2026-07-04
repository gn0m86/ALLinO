"use client"

import { useEffect, useRef, useState } from "react"

import { fetchAudit } from "../lib/api"
import { AuditLogEntry } from "../lib/types"

const AUDIT_LIMIT = 200

function formatTime(value: string): string {
	const d = new Date(value)
	if (Number.isNaN(d.getTime())) return value
	return d.toLocaleString("en", {
		month: "short",
		day: "2-digit",
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit",
	})
}

function actionColor(action: string): string {
	const a = action.toLowerCase()
	if (a.includes("error") || a.includes("reject") || a.includes("mismatch")) return "var(--danger)"
	if (a.includes("degraded") || a.includes("retry")) return "var(--warning)"
	return "var(--text-2)"
}

export function SecurityCenter() {
	const [entries, setEntries] = useState<AuditLogEntry[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)
	const disposedRef = useRef(false)

	const load = () => {
		const controller = new AbortController()
		setLoading(true)
		setError(null)
		fetchAudit(AUDIT_LIMIT, controller.signal)
			.then((data) => {
				if (disposedRef.current) return
				setEntries(data)
			})
			.catch((e: unknown) => {
				if (e instanceof DOMException && e.name === "AbortError") return
				if (disposedRef.current) return
				setError(e instanceof Error ? e.message : "Failed to load audit log")
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
					Security Center
				</h2>
				<div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
					{entries.length > 0 ? `${entries.length} recent events` : null}
				</div>
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
						Loading audit log…
					</div>
				)}

				{!loading && error && (
					<div
						style={{
							margin: 20,
							padding: "10px 14px",
							background: "var(--danger-soft)",
							color: "var(--danger)",
							borderRadius: "var(--r-card)",
							fontSize: 13,
							display: "flex",
							alignItems: "center",
							gap: 12,
						}}
					>
						<span>Failed to load audit log — {error}</span>
						<button
							onClick={() => load()}
							style={{
								fontSize: 12,
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

				{!loading && !error && entries.length === 0 && (
					<div
						style={{
							padding: "32px 16px",
							textAlign: "center",
							color: "var(--text-3)",
							fontSize: 13,
							fontFamily: "var(--font-mono)",
						}}
					>
						No audit events recorded yet for this tenant.
					</div>
				)}

				{!loading && !error && entries.length > 0 && (
					<div role="list" style={{ margin: "8px 20px 20px" }}>
						{entries.map((entry) => (
							<div
								key={entry.id}
								role="listitem"
								style={{
									display: "grid",
									gridTemplateColumns: "150px 1fr 120px",
									gap: 12,
									padding: "8px 4px",
									borderBottom: "1px solid var(--border)",
									fontSize: 12,
									alignItems: "start",
								}}
							>
								<span style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
									{formatTime(entry.created_at)}
								</span>
								<div>
									<div style={{ color: actionColor(entry.action), fontFamily: "var(--font-mono)" }}>
										{entry.action}
									</div>
									{entry.metadata && entry.metadata !== "{}" && (
										<div
											style={{
												marginTop: 2,
												color: "var(--text-3)",
												fontFamily: "var(--font-mono)",
												fontSize: 11,
												wordBreak: "break-all",
											}}
										>
											{entry.metadata}
										</div>
									)}
								</div>
								<span style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11, textAlign: "right" }}>
									{entry.actor ?? "system"}
								</span>
							</div>
						))}
					</div>
				)}
			</div>
		</div>
	)
}
