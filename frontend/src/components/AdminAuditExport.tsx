"use client"

import { useState } from "react"

import { exportTenantAudit, RUNTIME_CONFIG } from "../lib/api"

function downloadJson(filename: string, data: unknown) {
	const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
	const url = URL.createObjectURL(blob)
	const anchor = document.createElement("a")
	anchor.href = url
	anchor.download = filename
	anchor.click()
	URL.revokeObjectURL(url)
}

export function AdminAuditExport() {
	const [totpCode, setTotpCode] = useState("")
	const [pending, setPending] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [successCount, setSuccessCount] = useState<number | null>(null)

	const canSubmit = totpCode.trim().length > 0 && !pending

	async function handleExport() {
		if (!canSubmit) return
		setPending(true)
		setError(null)
		setSuccessCount(null)
		try {
			const result = await exportTenantAudit(totpCode.trim())
			downloadJson(`${RUNTIME_CONFIG.tenantId}-audit-export.json`, result)
			setSuccessCount(result.exported_count)
			setTotpCode("")
		} catch (e: unknown) {
			setError(e instanceof Error ? e.message : "Failed to export audit log")
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
				Export Audit Log
			</div>

			<p style={{ fontSize: 12, color: "var(--text-2)", margin: "0 0 12px" }}>
				Download the full audit log for this tenant as a JSON file. Requires a valid
				admin TOTP code — a second factor checked in addition to normal authentication.
			</p>

			<div style={{ display: "grid", gap: 8, maxWidth: 420 }}>
				<div>
					<label
						htmlFor="admin-export-totp"
						style={{ fontSize: 11, color: "var(--text-3)", display: "block", marginBottom: 4 }}
					>
						Admin TOTP code
					</label>
					<input
						id="admin-export-totp"
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
					onClick={() => void handleExport()}
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
					{pending ? "Exporting…" : "Export audit log"}
				</button>

				{error && (
					<div style={{ fontSize: 12, color: "var(--danger)" }}>{error}</div>
				)}
				{successCount !== null && (
					<div style={{ fontSize: 12, color: "var(--success)" }}>
						Exported {successCount} audit entr{successCount === 1 ? "y" : "ies"}.
					</div>
				)}
			</div>
		</div>
	)
}
