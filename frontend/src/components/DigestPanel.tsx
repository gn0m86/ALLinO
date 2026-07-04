"use client"

import { useEffect, useState } from "react"

import { fetchDigest } from "../lib/api"
import { DigestResponse, InboxMessage } from "../lib/types"
import { InboxList } from "./InboxList"

type Props = {
	selectedId: string | null
	onSelect: (item: InboxMessage) => void
}

const PRIORITY_LABELS: Record<string, string> = {
	high: "High",
	medium: "Medium",
	normal: "Normal",
}

export function DigestPanel({ selectedId, onSelect }: Props) {
	const [digest, setDigest] = useState<DigestResponse | null>(null)
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		let disposed = false
		const controller = new AbortController()
		setLoading(true)
		setError(null)
		fetchDigest(24, controller.signal)
			.then((data) => {
				if (!disposed) setDigest(data)
			})
			.catch((e: unknown) => {
				if (e instanceof DOMException && e.name === "AbortError") return
				if (!disposed) setError(e instanceof Error ? e.message : "Failed to load digest")
			})
			.finally(() => {
				if (!disposed) setLoading(false)
			})
		return () => {
			disposed = true
			controller.abort()
		}
	}, [])

	if (loading) {
		return (
			<div style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-3)", fontSize: 13, fontFamily: "var(--font-mono)" }}>
				Loading digest…
			</div>
		)
	}

	if (error) {
		return (
			<div style={{ margin: 12, padding: "10px 14px", background: "var(--danger-soft)", color: "var(--danger)", borderRadius: "var(--r-card)", fontSize: 13 }}>
				{error}
			</div>
		)
	}

	if (!digest) return null

	return (
		<div style={{ flex: 1, overflowY: "auto" }}>
			<div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)" }}>
				<div style={{ fontSize: 13, color: "var(--text)", marginBottom: 10 }}>
					<strong>{digest.total}</strong> new message{digest.total === 1 ? "" : "s"} in the last {digest.since_hours}h
				</div>

				{Object.keys(digest.by_source).length > 0 && (
					<div style={{ display: "grid", gap: 4, marginBottom: 10 }}>
						{Object.entries(digest.by_source).map(([source, count]) => (
							<div key={source} style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
								<span style={{ color: "var(--text-2)", textTransform: "capitalize" }}>{source}</span>
								<span style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>{count}</span>
							</div>
						))}
					</div>
				)}

				{Object.keys(digest.by_priority).length > 0 && (
					<div style={{ display: "flex", gap: 8 }}>
						{Object.entries(digest.by_priority).map(([priority, count]) => (
							<span
								key={priority}
								style={{
									fontSize: 11,
									fontFamily: "var(--font-mono)",
									padding: "2px 8px",
									borderRadius: 999,
									background: priority === "high" ? "var(--danger-soft)" : "var(--surface-2)",
									color: priority === "high" ? "var(--danger)" : "var(--text-3)",
								}}
							>
								{PRIORITY_LABELS[priority] ?? priority}: {count}
							</span>
						))}
					</div>
				)}
			</div>

			{digest.highlights.length > 0 ? (
				<>
					<div
						style={{
							padding: "10px 16px 4px",
							fontSize: 10,
							fontFamily: "var(--font-mono)",
							color: "var(--text-3)",
							textTransform: "uppercase",
							letterSpacing: "0.08em",
						}}
					>
						Highlights
					</div>
					<InboxList items={digest.highlights} selectedId={selectedId} onSelect={onSelect} />
				</>
			) : (
				digest.total === 0 && (
					<div style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-3)", fontSize: 13, fontFamily: "var(--font-mono)" }}>
						Nothing new in the last {digest.since_hours}h.
					</div>
				)
			)}
		</div>
	)
}
