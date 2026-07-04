"use client"

import { useEffect, useRef, useState } from "react"

import {
	deleteBuiltinConnectorSecret,
	fetchBuiltinConnectorSecrets,
	upsertBuiltinConnectorSecret,
} from "../lib/api"
import { BuiltinConnectorSecretSummary, BuiltinConnectorSourceType } from "../lib/types"

// Extra (beyond token) fields each source type accepts, mirroring
// backend/app/api/builtin_connector_secrets.py's _EXTRA_FIELDS. Sources not
// listed here only take a token.
const EXTRA_FIELDS: Partial<Record<BuiltinConnectorSourceType, ("base_url" | "user_id" | "channel_id" | "calendar_id")[]>> = {
	gitlab: ["base_url"],
	jira: ["base_url"],
	slack: ["channel_id"],
	discord: ["channel_id"],
	rocketchat: ["user_id", "base_url", "channel_id"],
	google_calendar: ["calendar_id"],
}

const SOURCE_LABELS: Record<BuiltinConnectorSourceType, string> = {
	github: "GitHub",
	gitlab: "GitLab",
	jira: "Jira",
	linear: "Linear",
	telegram: "Telegram",
	slack: "Slack",
	discord: "Discord",
	zoom: "Zoom",
	teams: "Teams",
	rocketchat: "Rocket.Chat",
	google_calendar: "Google Calendar",
}

const ALL_SOURCES = Object.keys(SOURCE_LABELS) as BuiltinConnectorSourceType[]

const FIELD_LABELS: Record<string, string> = {
	base_url: "Base URL",
	user_id: "User ID",
	channel_id: "Channel ID",
	calendar_id: "Calendar ID",
}

const inputStyle: React.CSSProperties = {
	width: "100%",
	padding: "6px 8px",
	background: "var(--bg)",
	border: "1px solid var(--border)",
	borderRadius: "var(--r-btn)",
	fontFamily: "var(--font-ui)",
	fontSize: 12.5,
	color: "var(--text)",
}

const labelStyle: React.CSSProperties = {
	display: "block",
	fontSize: 10,
	fontFamily: "var(--font-mono)",
	color: "var(--text-3)",
	textTransform: "uppercase",
	letterSpacing: "0.06em",
	marginBottom: 4,
}

type FormState = {
	token: string
	base_url: string
	user_id: string
	channel_id: string
	calendar_id: string
	poll_interval_seconds: string
}

const EMPTY_FORM: FormState = {
	token: "",
	base_url: "",
	user_id: "",
	channel_id: "",
	calendar_id: "",
	poll_interval_seconds: "",
}

export function BuiltinConnectorSecretsPanel() {
	const [configured, setConfigured] = useState<Record<string, BuiltinConnectorSecretSummary>>({})
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)
	const [openSource, setOpenSource] = useState<BuiltinConnectorSourceType | null>(null)
	const [form, setForm] = useState<FormState>(EMPTY_FORM)
	const [submitting, setSubmitting] = useState(false)
	const [formError, setFormError] = useState<string | null>(null)
	const [deletingSource, setDeletingSource] = useState<BuiltinConnectorSourceType | null>(null)
	const disposedRef = useRef(false)

	const load = () => {
		const controller = new AbortController()
		setLoading(true)
		setError(null)
		fetchBuiltinConnectorSecrets(controller.signal)
			.then((rows) => {
				if (disposedRef.current) return
				setConfigured(Object.fromEntries(rows.map((r) => [r.source_type, r])))
			})
			.catch((e: unknown) => {
				if (e instanceof DOMException && e.name === "AbortError") return
				if (disposedRef.current) return
				setError(e instanceof Error ? e.message : "Failed to load builtin connector secrets")
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

	function openForm(source: BuiltinConnectorSourceType) {
		setOpenSource(openSource === source ? null : source)
		setForm(EMPTY_FORM)
		setFormError(null)
	}

	async function handleSubmit(source: BuiltinConnectorSourceType) {
		if (submitting) return
		if (!form.token.trim()) {
			setFormError("Token is required.")
			return
		}
		const extras = EXTRA_FIELDS[source] ?? []
		for (const field of extras) {
			if ((source === "rocketchat" && (field === "user_id" || field === "base_url")) && !form[field].trim()) {
				setFormError(`${FIELD_LABELS[field]} is required for Rocket.Chat.`)
				return
			}
		}
		setSubmitting(true)
		setFormError(null)
		try {
			const summary = await upsertBuiltinConnectorSecret(source, {
				token: form.token.trim(),
				base_url: extras.includes("base_url") ? form.base_url.trim() || null : undefined,
				user_id: extras.includes("user_id") ? form.user_id.trim() || null : undefined,
				channel_id: extras.includes("channel_id") ? form.channel_id.trim() || null : undefined,
				calendar_id: extras.includes("calendar_id") ? form.calendar_id.trim() || null : undefined,
				poll_interval_seconds: form.poll_interval_seconds.trim() ? Number(form.poll_interval_seconds) : null,
			})
			setConfigured((prev) => ({ ...prev, [source]: summary }))
			setOpenSource(null)
			setForm(EMPTY_FORM)
		} catch (e: unknown) {
			setFormError(e instanceof Error ? e.message : "Failed to save secret")
		} finally {
			setSubmitting(false)
		}
	}

	async function handleDelete(source: BuiltinConnectorSourceType) {
		setDeletingSource(source)
		try {
			await deleteBuiltinConnectorSecret(source)
			setConfigured((prev) => {
				const next = { ...prev }
				delete next[source]
				return next
			})
		} catch (e: unknown) {
			setError(e instanceof Error ? e.message : "Failed to delete secret")
		} finally {
			setDeletingSource(null)
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
			<div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
				Your Own Credentials (Built-in Connectors)
			</div>
			<div style={{ fontSize: 11.5, color: "var(--text-3)", marginBottom: 10 }}>
				Bring your own token for GitHub/Jira/etc. instead of relying on the
				deployment-wide credential. Set a poll interval to auto-sync.
			</div>

			{loading && (
				<div style={{ fontSize: 12, color: "var(--text-3)", fontFamily: "var(--font-mono)", padding: "8px 0" }}>
					Loading…
				</div>
			)}

			{!loading && error && (
				<div
					style={{
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

			{!loading && !error && (
				<div role="list">
					{ALL_SOURCES.map((source) => {
						const summary = configured[source]
						const extras = EXTRA_FIELDS[source] ?? []
						return (
							<div key={source} style={{ borderTop: "1px solid var(--border)", padding: "8px 0" }} role="listitem">
								<div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8, alignItems: "center" }}>
									<div>
										<div style={{ color: "var(--text)", fontWeight: 500, fontSize: 12.5 }}>{SOURCE_LABELS[source]}</div>
										<div style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11, marginTop: 2 }}>
											{summary
												? `configured · poll: ${summary.poll_interval_seconds ? `${summary.poll_interval_seconds}s` : "off"}`
												: "not configured"}
										</div>
									</div>
									<div style={{ display: "flex", gap: 6 }}>
										<button
											onClick={() => openForm(source)}
											aria-label={`${summary ? "Edit" : "Configure"} ${SOURCE_LABELS[source]} credentials`}
											style={{
												fontSize: 11,
												fontFamily: "var(--font-mono)",
												color: "var(--accent)",
												background: "transparent",
												border: "1px solid var(--border)",
												borderRadius: "var(--r-btn)",
												padding: "4px 8px",
												cursor: "pointer",
												whiteSpace: "nowrap",
											}}
										>
											{openSource === source ? "Cancel" : summary ? "Edit" : "+ Configure"}
										</button>
										{summary && (
											<button
												onClick={() => void handleDelete(source)}
												disabled={deletingSource === source}
												aria-label={`Delete ${SOURCE_LABELS[source]} credentials`}
												style={{
													fontSize: 11,
													fontFamily: "var(--font-mono)",
													color: "var(--danger)",
													background: "transparent",
													border: "1px solid var(--border)",
													borderRadius: "var(--r-btn)",
													padding: "4px 8px",
													cursor: deletingSource === source ? "default" : "pointer",
													opacity: deletingSource === source ? 0.6 : 1,
												}}
											>
												{deletingSource === source ? "…" : "Delete"}
											</button>
										)}
									</div>
								</div>

								{openSource === source && (
									<div
										style={{
											border: "1px solid var(--border)",
											borderRadius: "var(--r-card)",
											background: "var(--bg)",
											padding: 12,
											marginTop: 8,
											display: "grid",
											gap: 8,
										}}
									>
										<div>
											<label style={labelStyle} htmlFor={`bc-token-${source}`}>Token</label>
											<input
												id={`bc-token-${source}`}
												style={inputStyle}
												type="password"
												value={form.token}
												onChange={(e) => setForm({ ...form, token: e.target.value })}
												placeholder={summary ? "Enter a new token to replace the stored one" : "Token"}
											/>
										</div>
										{extras.map((field) => (
											<div key={field}>
												<label style={labelStyle} htmlFor={`bc-${field}-${source}`}>{FIELD_LABELS[field]}</label>
												<input
													id={`bc-${field}-${source}`}
													style={inputStyle}
													value={form[field]}
													onChange={(e) => setForm({ ...form, [field]: e.target.value })}
												/>
											</div>
										))}
										<div>
											<label style={labelStyle} htmlFor={`bc-poll-${source}`}>Poll interval (seconds, optional)</label>
											<input
												id={`bc-poll-${source}`}
												style={inputStyle}
												type="number"
												min={30}
												max={86400}
												value={form.poll_interval_seconds}
												onChange={(e) => setForm({ ...form, poll_interval_seconds: e.target.value })}
												placeholder="300"
											/>
										</div>

										{formError && <div style={{ fontSize: 12, color: "var(--danger)" }}>{formError}</div>}

										<div>
											<button
												onClick={() => void handleSubmit(source)}
												disabled={submitting}
												style={{
													padding: "6px 14px",
													background: "var(--accent)",
													color: "var(--accent-fg)",
													border: "none",
													borderRadius: "var(--r-btn)",
													fontSize: 12.5,
													fontFamily: "var(--font-ui)",
													fontWeight: 500,
													cursor: submitting ? "default" : "pointer",
													opacity: submitting ? 0.6 : 1,
												}}
											>
												{submitting ? "Saving…" : "Save"}
											</button>
										</div>
									</div>
								)}
							</div>
						)
					})}
				</div>
			)}
		</div>
	)
}
