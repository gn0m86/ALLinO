"use client"

import { useMemo, useState } from "react"

import { ConnectorRun, ConnectorStatus } from "../lib/types"
import { useTimePrefs } from "../lib/timePrefs"

type Props = {
	connectors?: ConnectorStatus[]
	runs?: ConnectorRun[]
	refreshing?: boolean
	lastUpdatedAt?: string | null
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

export function ConnectorOpsPanel({ connectors = [], runs = [], refreshing = false, lastUpdatedAt = null }: Props) {
	const [sourceFilter, setSourceFilter] = useState<string>("all")
	const [statusFilter, setStatusFilter] = useState<string>("all")
	const [selectedRunId, setSelectedRunId] = useState<number | null>(null)
	const timePrefs = useTimePrefs()

	function formatTime(value: string | null | undefined): string {
		if (!value) return "n/a"
		const d = new Date(value)
		if (Number.isNaN(d.getTime())) return "n/a"
		return d.toLocaleTimeString("en-GB", {
			timeZone: timePrefs.myTimezone,
			hour: "2-digit",
			minute: "2-digit",
			second: "2-digit",
			hour12: timePrefs.hourCycle === "12h",
		})
	}

	const sourceOptions = useMemo(() => {
		const set = new Set<string>(runs.map((r) => r.source_type.toLowerCase()))
		return ["all", ...Array.from(set).sort()]
	}, [runs])

	const statusOptions = useMemo(() => {
		const set = new Set<string>(runs.map((r) => r.status.toLowerCase()))
		return ["all", ...Array.from(set).sort()]
	}, [runs])

	const filteredRuns = useMemo(() => {
		return runs.filter((run) => {
			const bySource = sourceFilter === "all" || run.source_type.toLowerCase() === sourceFilter
			const byStatus = statusFilter === "all" || run.status.toLowerCase() === statusFilter
			return bySource && byStatus
		})
	}, [runs, sourceFilter, statusFilter])

	const selectedRun = filteredRuns.find((r) => r.id === selectedRunId) ?? null

	return (
		<div
			style={{
				margin: "20px",
				border: "1px solid var(--border)",
				borderRadius: "var(--r-card)",
				background: "var(--surface)",
				overflow: "hidden",
			}}
		>
			<div
				style={{
					display: "flex",
					alignItems: "center",
					gap: 10,
					padding: "12px 14px",
					borderBottom: "1px solid var(--border)",
				}}
			>
				<div
					style={{
						fontSize: 11,
						fontFamily: "var(--font-mono)",
						textTransform: "uppercase",
						letterSpacing: "0.08em",
						color: "var(--text-3)",
					}}
				>
					Connector Operations
				</div>
				<div style={{ display: "flex", alignItems: "center", gap: 8 }}>
					<select
						value={sourceFilter}
						onChange={(e) => {
							setSourceFilter(e.target.value)
							setSelectedRunId(null)
						}}
						style={{
							fontSize: 11,
							fontFamily: "var(--font-mono)",
							border: "1px solid var(--border)",
							borderRadius: "var(--r-chip)",
							background: "var(--surface-2)",
							color: "var(--text-2)",
							padding: "4px 6px",
						}}
					>
						{sourceOptions.map((opt) => (
							<option key={opt} value={opt}>
								{opt === "all" ? "source: all" : `source: ${opt}`}
							</option>
						))}
					</select>
					<select
						value={statusFilter}
						onChange={(e) => {
							setStatusFilter(e.target.value)
							setSelectedRunId(null)
						}}
						style={{
							fontSize: 11,
							fontFamily: "var(--font-mono)",
							border: "1px solid var(--border)",
							borderRadius: "var(--r-chip)",
							background: "var(--surface-2)",
							color: "var(--text-2)",
							padding: "4px 6px",
						}}
					>
						{statusOptions.map((opt) => (
							<option key={opt} value={opt}>
								{opt === "all" ? "status: all" : `status: ${opt}`}
							</option>
						))}
					</select>
				</div>
				<div style={{ marginLeft: "auto", fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
					{refreshing ? "refreshing..." : `updated ${formatTime(lastUpdatedAt)}`}
				</div>
			</div>

			<div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
				<div style={{ padding: "12px 14px", borderRight: "1px solid var(--border)" }}>
					<div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
						Current Statuses
					</div>
					{connectors.length === 0 ? (
						<div style={{ fontSize: 12, color: "var(--text-3)" }}>No connector data yet</div>
					) : (
						connectors.slice(0, 6).map((c) => (
							<div
								key={c.id}
								style={{
									display: "grid",
									gridTemplateColumns: "1fr auto auto",
									gap: 8,
									fontSize: 12,
									padding: "6px 0",
									borderTop: "1px solid var(--border)",
								}}
							>
								<span style={{ color: "var(--text-2)", textTransform: "capitalize" }}>{c.source_type}</span>
								<span style={{ color: statusColor(c.status), textTransform: "uppercase", fontFamily: "var(--font-mono)", fontSize: 10 }}>
									{c.status}
								</span>
								<span style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 10 }}>
									{formatTime(c.last_synced_at)}
								</span>
							</div>
						))
					)}
				</div>

				<div style={{ padding: "12px 14px" }}>
					<div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
						Recent Runs ({filteredRuns.length})
					</div>
					{filteredRuns.length === 0 ? (
						<div style={{ fontSize: 12, color: "var(--text-3)" }}>No runs captured yet</div>
					) : (
						filteredRuns.slice(0, 8).map((run) => (
							<div
								key={run.id}
								title={run.error ?? undefined}
								onClick={() => setSelectedRunId(run.id)}
								style={{
									display: "grid",
									gridTemplateColumns: "1fr auto",
									gap: 8,
									padding: "6px 0",
									borderTop: "1px solid var(--border)",
									cursor: "pointer",
									background: selectedRunId === run.id ? "var(--surface-2)" : "transparent",
								}}
							>
								<div>
									<div style={{ fontSize: 12, color: "var(--text-2)", textTransform: "capitalize" }}>
										{run.source_type} · <span style={{ color: statusColor(run.status), fontFamily: "var(--font-mono)", fontSize: 10 }}>{run.status}</span>
									</div>
									<div style={{ fontSize: 10, color: run.error ? "var(--warning)" : "var(--text-3)", fontFamily: "var(--font-mono)" }}>
										{`p:${run.processed} i:${run.inserted} d:${run.duplicates} r:${run.rejected}`}
										{run.error ? " | error" : ""}
									</div>
								</div>
								<div style={{ fontSize: 10, color: "var(--text-3)", fontFamily: "var(--font-mono)" }}>
									{formatTime(run.synced_at)}
								</div>
							</div>
						))
					)}
				</div>
			</div>

			{selectedRun && (
				<div
					style={{
						borderTop: "1px solid var(--border)",
						padding: "10px 14px",
						background: "var(--surface-2)",
					}}
				>
					<div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
						Run Details
					</div>
					<div style={{ marginTop: 6, fontSize: 12, color: "var(--text-2)", fontFamily: "var(--font-mono)" }}>
						{`id:${selectedRun.id} source:${selectedRun.source_type} status:${selectedRun.status} synced:${formatTime(selectedRun.synced_at)}`}
					</div>
					<div style={{ marginTop: 4, fontSize: 11, color: "var(--text-3)", fontFamily: "var(--font-mono)" }}>
						{`processed:${selectedRun.processed} inserted:${selectedRun.inserted} duplicates:${selectedRun.duplicates} rejected:${selectedRun.rejected}`}
					</div>
					{selectedRun.error && (
						<div style={{ marginTop: 4, fontSize: 11, color: "var(--warning)", fontFamily: "var(--font-mono)" }}>
							{`error: ${selectedRun.error}`}
						</div>
					)}
				</div>
			)}
		</div>
	)
}
