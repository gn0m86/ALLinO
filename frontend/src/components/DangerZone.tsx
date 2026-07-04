"use client"

import { useState } from "react"

import { deleteAllTenantMessages, RUNTIME_CONFIG } from "../lib/api"

export function DangerZone() {
	const [confirmText, setConfirmText] = useState("")
	const [totpCode, setTotpCode] = useState("")
	const [pending, setPending] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [successCount, setSuccessCount] = useState<number | null>(null)

	const canSubmit = confirmText === RUNTIME_CONFIG.tenantId && totpCode.trim().length > 0 && !pending

	async function handleDelete() {
		if (!canSubmit) return
		setPending(true)
		setError(null)
		setSuccessCount(null)
		try {
			const result = await deleteAllTenantMessages(confirmText, totpCode.trim())
			setSuccessCount(result.deleted_count)
			setConfirmText("")
			setTotpCode("")
		} catch (e: unknown) {
			setError(e instanceof Error ? e.message : "Failed to delete tenant messages")
		} finally {
			setPending(false)
		}
	}

	return (
		<div
			style={{
				border: "1px solid var(--danger)",
				borderRadius: "var(--r-card)",
				background: "var(--danger-soft)",
				padding: "14px 16px",
				marginTop: 16,
			}}
		>
			<div
				style={{
					fontSize: 10,
					fontFamily: "var(--font-mono)",
					color: "var(--danger)",
					textTransform: "uppercase",
					letterSpacing: "0.08em",
					marginBottom: 8,
				}}
			>
				Danger Zone
			</div>

			<p style={{ fontSize: 12, color: "var(--text-2)", margin: "0 0 12px" }}>
				Permanently delete every message for this tenant (
				<span style={{ fontFamily: "var(--font-mono)" }}>{RUNTIME_CONFIG.tenantId}</span>
				). This cannot be undone. Requires a valid admin TOTP code — a second factor
				checked in addition to normal authentication.
			</p>

			<div style={{ display: "grid", gap: 8, maxWidth: 420 }}>
				<div>
					<label
						htmlFor="danger-zone-confirm"
						style={{ fontSize: 11, color: "var(--text-3)", display: "block", marginBottom: 4 }}
					>
						Type the tenant id ({RUNTIME_CONFIG.tenantId}) to confirm
					</label>
					<input
						id="danger-zone-confirm"
						value={confirmText}
						onChange={(e) => setConfirmText(e.target.value)}
						placeholder={RUNTIME_CONFIG.tenantId}
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
				<div>
					<label
						htmlFor="danger-zone-totp"
						style={{ fontSize: 11, color: "var(--text-3)", display: "block", marginBottom: 4 }}
					>
						Admin TOTP code
					</label>
					<input
						id="danger-zone-totp"
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
					onClick={() => void handleDelete()}
					disabled={!canSubmit}
					style={{
						justifySelf: "start",
						padding: "6px 14px",
						background: "var(--danger)",
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
					{pending ? "Deleting…" : "Delete all messages"}
				</button>

				{error && (
					<div style={{ fontSize: 12, color: "var(--danger)" }}>{error}</div>
				)}
				{successCount !== null && (
					<div style={{ fontSize: 12, color: "var(--success)" }}>
						Deleted {successCount} message{successCount === 1 ? "" : "s"}.
					</div>
				)}
			</div>
		</div>
	)
}
