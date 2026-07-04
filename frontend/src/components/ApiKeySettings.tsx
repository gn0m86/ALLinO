"use client"

import { useEffect, useState } from "react"

import { getStoredApiKey, setStoredApiKey } from "../lib/api"

export function ApiKeySettings() {
	const [value, setValue] = useState("")
	const [hasStoredKey, setHasStoredKey] = useState(false)
	const [statusMessage, setStatusMessage] = useState<string | null>(null)

	useEffect(() => {
		const existing = getStoredApiKey()
		if (existing) {
			setValue(existing)
			setHasStoredKey(true)
		}
	}, [])

	function handleSave() {
		const trimmed = value.trim()
		setStoredApiKey(trimmed || null)
		setHasStoredKey(Boolean(trimmed))
		setStatusMessage(trimmed ? "Saved — used on every request from now on." : "Cleared.")
	}

	function handleClear() {
		setValue("")
		setStoredApiKey(null)
		setHasStoredKey(false)
		setStatusMessage("Cleared.")
	}

	return (
		<div
			style={{
				border: "1px solid var(--border)",
				borderRadius: "var(--r-card)",
				background: "var(--surface)",
				padding: "14px 16px",
				marginBottom: 16,
			}}
		>
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
				Backend Access
			</div>

			<p style={{ fontSize: 12, color: "var(--text-2)", margin: "0 0 12px" }}>
				If the backend requires an API key (<span style={{ fontFamily: "var(--font-mono)" }}>ALLINO_API_KEY</span>),
				enter it here so this browser can authenticate. Stored only in this browser
				(<span style={{ fontFamily: "var(--font-mono)" }}>localStorage</span>), sent as{" "}
				<span style={{ fontFamily: "var(--font-mono)" }}>X-API-Key</span> on every request. Leave empty if
				the backend runs without a key (local development).
			</p>

			<div style={{ display: "grid", gap: 8, maxWidth: 420 }}>
				<div>
					<label
						htmlFor="settings-api-key"
						style={{ fontSize: 11, color: "var(--text-3)", display: "block", marginBottom: 4 }}
					>
						API key {hasStoredKey && <span style={{ color: "var(--success)" }}>(set)</span>}
					</label>
					<input
						id="settings-api-key"
						type="password"
						value={value}
						onChange={(e) => setValue(e.target.value)}
						placeholder="leave empty for unauthenticated backends"
						style={{
							width: "100%",
							boxSizing: "border-box",
							padding: "8px 10px",
							border: "1px solid var(--border)",
							borderRadius: "var(--r-btn)",
							background: "var(--bg)",
							color: "var(--text)",
							fontSize: 13,
							fontFamily: "var(--font-mono)",
							outline: "none",
						}}
					/>
				</div>

				<div style={{ display: "flex", gap: 8 }}>
					<button
						onClick={handleSave}
						style={{
							padding: "6px 14px",
							background: "var(--accent)",
							color: "var(--accent-fg)",
							border: "none",
							borderRadius: "var(--r-btn)",
							fontSize: 13,
							fontFamily: "var(--font-ui)",
							fontWeight: 500,
							cursor: "pointer",
						}}
					>
						Save
					</button>
					<button
						onClick={handleClear}
						style={{
							padding: "6px 14px",
							background: "transparent",
							color: "var(--text-2)",
							border: "1px solid var(--border)",
							borderRadius: "var(--r-btn)",
							fontSize: 13,
							fontFamily: "var(--font-ui)",
							fontWeight: 500,
							cursor: "pointer",
						}}
					>
						Clear
					</button>
				</div>

				{statusMessage && (
					<div style={{ fontSize: 12, color: "var(--text-3)" }}>{statusMessage}</div>
				)}
			</div>
		</div>
	)
}
