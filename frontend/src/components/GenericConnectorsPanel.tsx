"use client"

import { useEffect, useRef, useState } from "react"

import {
	createGenericConnector,
	deleteGenericConnector,
	fetchGenericConnectors,
	updateGenericConnector,
} from "../lib/api"
import { GenericConnectorAuthMethod, GenericConnectorConfig } from "../lib/types"

const AUTH_METHODS: { value: GenericConnectorAuthMethod; label: string }[] = [
	{ value: "none", label: "None" },
	{ value: "api_key", label: "API key header" },
	{ value: "bearer", label: "Bearer token" },
	{ value: "basic", label: "Basic auth" },
]

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
	name: string
	base_url: string
	auth_method: GenericConnectorAuthMethod
	auth_header_name: string
	poll_interval_seconds: string
	field_externalId: string
	field_timestamp: string
	field_preview: string
	field_items_path: string
	webhook_enabled: boolean
}

const EMPTY_FORM: FormState = {
	name: "",
	base_url: "",
	auth_method: "none",
	auth_header_name: "",
	poll_interval_seconds: "",
	field_externalId: "",
	field_timestamp: "",
	field_preview: "",
	field_items_path: "",
	webhook_enabled: false,
}

export function GenericConnectorsPanel() {
	const [configs, setConfigs] = useState<GenericConnectorConfig[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)
	const [formOpen, setFormOpen] = useState(false)
	const [form, setForm] = useState<FormState>(EMPTY_FORM)
	const [submitting, setSubmitting] = useState(false)
	const [formError, setFormError] = useState<string | null>(null)
	const [deletingId, setDeletingId] = useState<string | null>(null)
	const [editingId, setEditingId] = useState<string | null>(null)
	const disposedRef = useRef(false)

	const load = () => {
		const controller = new AbortController()
		setLoading(true)
		setError(null)
		fetchGenericConnectors(controller.signal)
			.then((data) => {
				if (disposedRef.current) return
				setConfigs(data)
			})
			.catch((e: unknown) => {
				if (e instanceof DOMException && e.name === "AbortError") return
				if (disposedRef.current) return
				setError(e instanceof Error ? e.message : "Failed to load generic connectors")
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

	function openCreateForm() {
		setEditingId(null)
		setForm(EMPTY_FORM)
		setFormError(null)
		setFormOpen(true)
	}

	function openEditForm(config: GenericConnectorConfig) {
		setEditingId(config.id)
		setForm({
			name: config.name,
			base_url: config.base_url ?? "",
			auth_method: config.auth_method,
			auth_header_name: config.auth_header_name ?? "",
			poll_interval_seconds: config.poll_interval_seconds != null ? String(config.poll_interval_seconds) : "",
			field_externalId: config.field_mapping.externalId,
			field_timestamp: config.field_mapping.timestamp,
			field_preview: config.field_mapping.preview ?? "",
			field_items_path: config.field_mapping.items_path ?? "",
			webhook_enabled: config.webhook_enabled,
		})
		setFormError(null)
		setFormOpen(true)
	}

	function closeForm() {
		setFormOpen(false)
		setEditingId(null)
		setForm(EMPTY_FORM)
	}

	async function handleSubmit() {
		if (submitting) return
		const externalId = form.field_externalId.trim()
		const timestamp = form.field_timestamp.trim()
		if (!editingId && !form.name.trim()) {
			setFormError("Name, externalId mapping, and timestamp mapping are required.")
			return
		}
		if (!externalId || !timestamp) {
			setFormError("Name, externalId mapping, and timestamp mapping are required.")
			return
		}
		if (form.auth_method === "api_key" && !form.auth_header_name.trim()) {
			setFormError("Auth header name is required for API key auth.")
			return
		}
		setSubmitting(true)
		setFormError(null)
		try {
			if (editingId) {
				await updateGenericConnector(editingId, {
					base_url: form.base_url.trim() || null,
					auth_method: form.auth_method,
					auth_header_name: form.auth_method === "api_key" ? form.auth_header_name.trim() : null,
					poll_interval_seconds: form.poll_interval_seconds.trim()
						? Number(form.poll_interval_seconds)
						: null,
					field_mapping: {
						externalId,
						timestamp,
						preview: form.field_preview.trim() || null,
						items_path: form.field_items_path.trim() || null,
					},
					webhook_enabled: form.webhook_enabled,
				})
			} else {
				await createGenericConnector({
					name: form.name.trim(),
					base_url: form.base_url.trim() || null,
					auth_method: form.auth_method,
					auth_header_name: form.auth_method === "api_key" ? form.auth_header_name.trim() : null,
					poll_interval_seconds: form.poll_interval_seconds.trim()
						? Number(form.poll_interval_seconds)
						: null,
					field_mapping: {
						externalId,
						timestamp,
						preview: form.field_preview.trim() || null,
						items_path: form.field_items_path.trim() || null,
					},
					webhook_enabled: form.webhook_enabled,
				})
			}
			closeForm()
			load()
		} catch (e: unknown) {
			setFormError(e instanceof Error ? e.message : (editingId ? "Failed to update connector" : "Failed to create connector"))
		} finally {
			setSubmitting(false)
		}
	}

	async function handleDelete(id: string) {
		setDeletingId(id)
		try {
			await deleteGenericConnector(id)
			setConfigs((prev) => prev.filter((c) => c.id !== id))
		} catch (e: unknown) {
			setError(e instanceof Error ? e.message : "Failed to delete connector")
		} finally {
			setDeletingId(null)
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
			<div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
				<div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
					Custom Connectors (Generic HTTP)
				</div>
				<button
					onClick={() => {
						if (formOpen) {
							closeForm()
						} else {
							openCreateForm()
						}
					}}
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
					{formOpen ? "Cancel" : "+ Add connector"}
				</button>
			</div>

			{formOpen && (
				<div
					style={{
						border: "1px solid var(--border)",
						borderRadius: "var(--r-card)",
						background: "var(--bg)",
						padding: 12,
						marginBottom: 12,
						display: "grid",
						gap: 8,
					}}
				>
					<div>
						<label style={labelStyle} htmlFor="gc-name">Name{editingId ? " (can't be changed)" : ""}</label>
						<input
							id="gc-name"
							style={editingId ? { ...inputStyle, opacity: 0.6, cursor: "not-allowed" } : inputStyle}
							value={form.name}
							disabled={!!editingId}
							onChange={(e) => setForm({ ...form, name: e.target.value })}
							placeholder="My internal API"
						/>
					</div>
					<div>
						<label style={labelStyle} htmlFor="gc-url">Base URL (optional — omit for webhook-only)</label>
						<input
							id="gc-url"
							style={inputStyle}
							value={form.base_url}
							onChange={(e) => setForm({ ...form, base_url: e.target.value })}
							placeholder="https://api.example.com/events"
						/>
					</div>
					<div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
						<div>
							<label style={labelStyle} htmlFor="gc-auth">Auth method</label>
							<select
								id="gc-auth"
								style={inputStyle}
								value={form.auth_method}
								onChange={(e) => setForm({ ...form, auth_method: e.target.value as GenericConnectorAuthMethod })}
							>
								{AUTH_METHODS.map((m) => (
									<option key={m.value} value={m.value}>{m.label}</option>
								))}
							</select>
						</div>
						<div>
							<label style={labelStyle} htmlFor="gc-poll">Poll interval (seconds, optional)</label>
							<input
								id="gc-poll"
								style={inputStyle}
								type="number"
								min={30}
								max={86400}
								value={form.poll_interval_seconds}
								onChange={(e) => setForm({ ...form, poll_interval_seconds: e.target.value })}
								placeholder="300"
							/>
						</div>
					</div>
					{form.auth_method === "api_key" && (
						<div>
							<label style={labelStyle} htmlFor="gc-authheader">Auth header name</label>
							<input
								id="gc-authheader"
								style={inputStyle}
								value={form.auth_header_name}
								onChange={(e) => setForm({ ...form, auth_header_name: e.target.value })}
								placeholder="X-API-Key"
							/>
						</div>
					)}
					<div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
						<div>
							<label style={labelStyle} htmlFor="gc-fid">Field: externalId</label>
							<input
								id="gc-fid"
								style={inputStyle}
								value={form.field_externalId}
								onChange={(e) => setForm({ ...form, field_externalId: e.target.value })}
								placeholder="id"
							/>
						</div>
						<div>
							<label style={labelStyle} htmlFor="gc-fts">Field: timestamp</label>
							<input
								id="gc-fts"
								style={inputStyle}
								value={form.field_timestamp}
								onChange={(e) => setForm({ ...form, field_timestamp: e.target.value })}
								placeholder="created_at"
							/>
						</div>
						<div>
							<label style={labelStyle} htmlFor="gc-fpv">Field: preview (optional)</label>
							<input
								id="gc-fpv"
								style={inputStyle}
								value={form.field_preview}
								onChange={(e) => setForm({ ...form, field_preview: e.target.value })}
								placeholder="title"
							/>
						</div>
					</div>
					<div>
						<label style={labelStyle} htmlFor="gc-items">
							Items path (optional — for nested/array payloads, e.g. WhatsApp)
						</label>
						<input
							id="gc-items"
							style={inputStyle}
							value={form.field_items_path}
							onChange={(e) => setForm({ ...form, field_items_path: e.target.value })}
							placeholder="entry[].changes[].value.messages[]"
						/>
					</div>
					<label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-2)" }}>
						<input
							type="checkbox"
							checked={form.webhook_enabled}
							onChange={(e) => setForm({ ...form, webhook_enabled: e.target.checked })}
						/>
						Enable webhook receiver for this connector
					</label>

					{formError && (
						<div style={{ fontSize: 12, color: "var(--danger)" }}>{formError}</div>
					)}

					<div>
						<button
							onClick={() => void handleSubmit()}
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
							{submitting
								? (editingId ? "Saving…" : "Creating…")
								: (editingId ? "Save changes" : "Create connector")}
						</button>
					</div>
				</div>
			)}

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

			{!loading && !error && configs.length === 0 && (
				<div style={{ fontSize: 12, color: "var(--text-3)" }}>
					No custom connectors registered yet.
				</div>
			)}

			{!loading && !error && configs.length > 0 && (
				<div role="list">
					{configs.map((c) => (
						<div
							key={c.id}
							role="listitem"
							style={{
								display: "grid",
								gridTemplateColumns: "1fr auto",
								gap: 8,
								padding: "8px 0",
								borderTop: "1px solid var(--border)",
								fontSize: 12,
								alignItems: "start",
							}}
						>
							<div>
								<div style={{ color: "var(--text)", fontWeight: 500 }}>{c.name}</div>
								<div style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11, marginTop: 2 }}>
									slug: {c.slug} · auth: {c.auth_method}
									{c.base_url ? ` · ${c.base_url}` : ""}
								</div>
								{c.webhook_enabled && c.webhook_url && (
									<div style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11, marginTop: 2, wordBreak: "break-all" }}>
										webhook: {c.webhook_url}
									</div>
								)}
							</div>
							<div style={{ display: "flex", gap: 6 }}>
								<button
									onClick={() => openEditForm(c)}
									aria-label={`Edit connector ${c.name}`}
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
									Edit
								</button>
								<button
									onClick={() => void handleDelete(c.id)}
									disabled={deletingId === c.id}
									aria-label={`Delete connector ${c.name}`}
									style={{
										fontSize: 11,
										fontFamily: "var(--font-mono)",
										color: "var(--danger)",
										background: "transparent",
										border: "1px solid var(--border)",
										borderRadius: "var(--r-btn)",
										padding: "4px 8px",
										cursor: deletingId === c.id ? "default" : "pointer",
										opacity: deletingId === c.id ? 0.6 : 1,
									}}
								>
									{deletingId === c.id ? "…" : "Delete"}
								</button>
							</div>
						</div>
					))}
				</div>
			)}
		</div>
	)
}
