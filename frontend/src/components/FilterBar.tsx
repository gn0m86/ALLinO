"use client"

import { Priority } from "../lib/types"

export type FilterState = {
	source: string | null
	priority: Priority | null
}

type Props = {
	filters: FilterState
	availableSources: string[]
	onChange: (f: FilterState) => void
}

const PRIORITY_OPTS: { value: Priority; label: string; color: string; bg: string }[] = [
	{ value: "high",   label: "High",   color: "var(--danger)",  bg: "var(--danger-soft)" },
	{ value: "medium", label: "Medium", color: "var(--warning)", bg: "var(--warning-soft)" },
]

export function FilterBar({ filters, availableSources, onChange }: Props) {
	const hasFilter = filters.source !== null || filters.priority !== null

	function setSource(s: string | null) {
		onChange({ ...filters, source: filters.source === s ? null : s })
	}

	function setPriority(p: Priority | null) {
		onChange({ ...filters, priority: filters.priority === p ? null : p })
	}

	function clearAll() {
		onChange({ source: null, priority: null })
	}

	return (
		<div
			style={{
				display: "flex",
				alignItems: "center",
				gap: 6,
				padding: "6px 12px",
				borderBottom: "1px solid var(--border)",
				flexShrink: 0,
				flexWrap: "wrap",
				background: "var(--surface)",
			}}
		>
			{/* Source chips */}
			{availableSources.map((src) => {
				const active = filters.source === src
				return (
					<button
						key={src}
						onClick={() => setSource(src)}
						aria-pressed={active}
						style={{
							display: "inline-flex",
							alignItems: "center",
							height: 22,
							padding: "0 8px",
							borderRadius: "var(--r-chip)",
							border: active ? "1.5px solid var(--accent)" : "1px solid var(--border)",
							background: active ? "var(--accent-soft)" : "var(--surface-2)",
							color: active ? "var(--accent)" : "var(--text-2)",
							fontSize: 11,
							fontFamily: "var(--font-mono)",
							fontWeight: active ? 600 : 400,
							cursor: "pointer",
							transition: "all 0.1s",
						}}
					>
						{src}
					</button>
				)
			})}

			{/* Divider */}
			{availableSources.length > 0 && (
				<div
					style={{
						width: 1,
						height: 14,
						background: "var(--border)",
						flexShrink: 0,
					}}
				/>
			)}

			{/* Priority chips */}
			{PRIORITY_OPTS.map((opt) => {
				const active = filters.priority === opt.value
				return (
					<button
						key={opt.value}
						onClick={() => setPriority(opt.value)}
						aria-pressed={active}
						style={{
							display: "inline-flex",
							alignItems: "center",
							height: 22,
							padding: "0 8px",
							borderRadius: "var(--r-chip)",
							border: active ? `1.5px solid ${opt.color}` : "1px solid var(--border)",
							background: active ? opt.bg : "var(--surface-2)",
							color: active ? opt.color : "var(--text-2)",
							fontSize: 11,
							fontFamily: "var(--font-mono)",
							fontWeight: active ? 600 : 400,
							cursor: "pointer",
							transition: "all 0.1s",
						}}
					>
						{opt.label}
					</button>
				)
			})}

			{/* Clear */}
			{hasFilter && (
				<>
					<div style={{ flex: 1 }} />
					<button
						onClick={clearAll}
						style={{
							display: "inline-flex",
							alignItems: "center",
							height: 22,
							padding: "0 8px",
							borderRadius: "var(--r-chip)",
							border: "none",
							background: "transparent",
							color: "var(--text-3)",
							fontSize: 11,
							fontFamily: "var(--font-mono)",
							cursor: "pointer",
						}}
					>
						clear ×
					</button>
				</>
			)}
		</div>
	)
}
