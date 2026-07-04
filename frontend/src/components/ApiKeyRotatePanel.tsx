"use client"

import { useState } from "react"

import { rotateApiKeyCandidate } from "../lib/api"

export function ApiKeyRotatePanel() {
	const [totpCode, setTotpCode] = useState("")
	const [pending, setPending] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [result, setResult] = useState<{ candidate_api_key: string; instructions: string } | null>(null)

	const canSubmit = totpCode.trim().length > 0 && !pending

	async function handleRotate() {
		if (!canSubmit) return
		setPending(true)
		setError(null)
		setResult(null)
		try {
			const response = await rotateApiKeyCandidate(totpCode.trim())
			setResult(response)
			setTotpCode("")
		} catch (e: unknown) {
			setError(e instanceof Error ? e.message : "Failed to generate a candidate API key")
		} finally {
			setPending(false)
		}
	}

	return (
		<div
			style={{
				border: "1px solid var(--border)",
				borderRadius: "var(--r-card)",
				background: "var(--surface)",
				padding: "14px 16px",
				marginTop: 16,
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
				Rotate API Key
			</div>

			<p style={{ fontSize: 12, color: "var(--text-2)", margin: "0 0 12px" }}>
				Generate a new random API key. This does not activate it — the current key
				keeps working until you manually set <span style={{ fontFamily: "var(--font-mono)" }}>ALLINO_API_KEY</span>{" "}
				to the new value and restart the backend. Requires a valid admin TOTP code.
			</p>

			<div style={{ display: "grid", gap: 8, maxWidth: 420 }}>
				<div>
					<label
						htmlFor="admin-rotate-totp"
						style={{ fontSize: 11, color: "var(--text-3)", display: "block", marginBottom: 4 }}
					>
						Admin TOTP code
					</label>
					<input
						id="admin-rotate-totp"
						value={totpCode}
						onChange={(e) => setTotpCode(e.target.value)}
						placeholder="123456"
						inputMode="numeric"
						disabled={pending}
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

				<button
					onClick={() => void handleRotate()}
					disabled={!canSubmit}
					style={{
						justifySelf: "start",
						padding: "6px 14px",
						background: "var(--accent)",
						color: "var(--accent-fg)",
						border: "none",
						borderRadius: "var(--r-btn)",
						fontSize: 13,
						fontFamily: "var(--font-ui)",
						fontWeight: 500,
						cursor: canSubmit ? "pointer" : "default",
						opacity: canSubmit ? 1 : 0.5,
					}}
				>
					{pending ? "Generating…" : "Generate new key"}
				</button>

				{error && (
					<div style={{ fontSize: 12, color: "var(--danger)" }}>{error}</div>
				)}
				{result && (
					<div style={{ display: "grid", gap: 6 }}>
						<label
							htmlFor="admin-rotate-result"
							style={{ fontSize: 11, color: "var(--text-3)" }}
						>
							New candidate key (shown once — copy it now)
						</label>
						<input
							id="admin-rotate-result"
							readOnly
							value={result.candidate_api_key}
							onFocus={(e) => e.currentTarget.select()}
							style={{
								width: "100%",
								boxSizing: "border-box",
								padding: "8px 10px",
								border: "1px solid var(--accent)",
								borderRadius: "var(--r-btn)",
								background: "var(--bg)",
								color: "var(--text)",
								fontSize: 12,
								fontFamily: "var(--font-mono)",
								outline: "none",
							}}
						/>
						<div style={{ fontSize: 12, color: "var(--success)" }}>{result.instructions}</div>
					</div>
				)}
			</div>
		</div>
	)
}
