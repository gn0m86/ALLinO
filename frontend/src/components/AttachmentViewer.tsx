"use client"

import { useEffect, useRef, useState } from "react"

import { fetchMessageAttachment } from "../lib/api"

type Props = {
	eventId: string
	attachmentType: "image" | "video" | "file"
	attachmentName?: string | null
	attachmentSize?: number | null
}

function ImageLightbox({ src, onClose }: { src: string; onClose: () => void }) {
	useEffect(() => {
		function onKeyDown(e: KeyboardEvent) {
			if (e.key === "Escape") onClose()
		}
		window.addEventListener("keydown", onKeyDown)
		return () => window.removeEventListener("keydown", onKeyDown)
	}, [onClose])

	return (
		<div
			onClick={onClose}
			role="dialog"
			aria-modal="true"
			aria-label="Full-size image"
			style={{
				position: "fixed",
				inset: 0,
				zIndex: 1000,
				background: "rgba(0, 0, 0, 0.85)",
				display: "flex",
				alignItems: "center",
				justifyContent: "center",
				cursor: "zoom-out",
			}}
		>
			<button
				onClick={onClose}
				aria-label="Close full-size image"
				style={{
					position: "absolute",
					top: 16,
					right: 16,
					width: 36,
					height: 36,
					borderRadius: "50%",
					border: "none",
					background: "rgba(255, 255, 255, 0.12)",
					color: "#FFFFFF",
					fontSize: 18,
					lineHeight: 1,
					cursor: "pointer",
				}}
			>
				×
			</button>
			{/* eslint-disable-next-line @next/next/no-img-element */}
			<img
				src={src}
				alt="Message attachment, full size"
				onClick={(e) => e.stopPropagation()}
				style={{ maxWidth: "92vw", maxHeight: "92vh", objectFit: "contain", cursor: "default" }}
			/>
		</div>
	)
}

function formatBytes(bytes?: number | null): string {
	if (bytes == null || bytes < 0) return ""
	if (bytes < 1024) return `${bytes} B`
	const units = ["KB", "MB", "GB"]
	let value = bytes / 1024
	let unitIndex = 0
	while (value >= 1024 && unitIndex < units.length - 1) {
		value /= 1024
		unitIndex++
	}
	return `${value.toFixed(value < 10 ? 1 : 0)} ${units[unitIndex]}`
}

// Recognized by extension only -- Rocket.Chat's own MIME type for office/archive
// formats is often a generic application/octet-stream, so the extension is the
// only reliable signal for which little colored badge to show.
const FILE_KIND_BY_EXTENSION: Record<string, { label: string; color: string }> = {
	pdf: { label: "PDF", color: "var(--danger)" },
	doc: { label: "DOC", color: "var(--info)" },
	docx: { label: "DOC", color: "var(--info)" },
	xls: { label: "XLS", color: "var(--success)" },
	xlsx: { label: "XLS", color: "var(--success)" },
	csv: { label: "CSV", color: "var(--success)" },
	ppt: { label: "PPT", color: "var(--warning)" },
	pptx: { label: "PPT", color: "var(--warning)" },
	zip: { label: "ZIP", color: "var(--text-2)" },
	rar: { label: "RAR", color: "var(--text-2)" },
	"7z": { label: "7Z", color: "var(--text-2)" },
	txt: { label: "TXT", color: "var(--text-2)" },
	mp3: { label: "MP3", color: "var(--accent)" },
	wav: { label: "WAV", color: "var(--accent)" },
}

function fileKind(name?: string | null): { label: string; color: string } {
	const ext = (name || "").split(".").pop()?.toLowerCase() || ""
	return FILE_KIND_BY_EXTENSION[ext] ?? { label: ext ? ext.slice(0, 4).toUpperCase() : "FILE", color: "var(--text-3)" }
}

// Click-to-load only -- never fetched automatically. Loading it always means the
// user explicitly asked to see it, so opening a message never itself reveals to
// the source server that its media was viewed unless the user requests it.
export function AttachmentViewer({ eventId, attachmentType, attachmentName, attachmentSize }: Props) {
	const [objectUrl, setObjectUrl] = useState<string | null>(null)
	const [loading, setLoading] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [fullscreen, setFullscreen] = useState(false)
	const objectUrlRef = useRef<string | null>(null)

	useEffect(() => {
		return () => {
			if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
		}
	}, [eventId])

	async function handleLoad() {
		setLoading(true)
		setError(null)
		try {
			const url = await fetchMessageAttachment(eventId)
			objectUrlRef.current = url

			if (attachmentType === "file") {
				// Blob URLs don't carry the backend's Content-Disposition header --
				// the `download` attribute is what actually makes the browser save
				// the file instead of trying to navigate to/render it.
				const link = document.createElement("a")
				link.href = url
				link.download = attachmentName || "attachment"
				link.click()
			}

			setObjectUrl(url)
		} catch (e: unknown) {
			setError(e instanceof Error ? e.message : "Failed to load attachment")
		} finally {
			setLoading(false)
		}
	}

	if (objectUrl && attachmentType === "image") {
		return (
			<>
				{/* eslint-disable-next-line @next/next/no-img-element */}
				<img
					src={objectUrl}
					alt="Message attachment"
					onClick={() => setFullscreen(true)}
					title="Click to view full size"
					style={{ maxWidth: "100%", maxHeight: 320, borderRadius: "var(--r-card)", marginTop: 8, display: "block", cursor: "zoom-in" }}
				/>
				{fullscreen && <ImageLightbox src={objectUrl} onClose={() => setFullscreen(false)} />}
			</>
		)
	}
	if (objectUrl && attachmentType === "video") {
		return (
			<video
				src={objectUrl}
				controls
				style={{ maxWidth: "100%", maxHeight: 320, borderRadius: "var(--r-card)", marginTop: 8, display: "block" }}
			/>
		)
	}

	if (attachmentType === "file") {
		const kind = fileKind(attachmentName)
		const sizeLabel = formatBytes(attachmentSize)
		const downloaded = objectUrl !== null

		return (
			<div
				style={{
					marginTop: 8,
					display: "flex",
					alignItems: "center",
					gap: 10,
					padding: "8px 10px",
					border: "1px solid var(--border)",
					borderRadius: "var(--r-card)",
					background: "var(--surface-2)",
					maxWidth: 320,
				}}
			>
				<div
					aria-hidden="true"
					style={{
						width: 34,
						height: 34,
						flexShrink: 0,
						borderRadius: "var(--r-chip)",
						background: kind.color,
						color: "#FFFFFF",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						fontSize: 9,
						fontWeight: 700,
						fontFamily: "var(--font-mono)",
					}}
				>
					{kind.label}
				</div>
				<div style={{ flex: 1, minWidth: 0 }}>
					<div style={{ fontSize: 13, color: "var(--text)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
						{attachmentName || "file"}
					</div>
					{sizeLabel && (
						<div style={{ fontSize: 11, color: "var(--text-3)", fontFamily: "var(--font-mono)" }}>{sizeLabel}</div>
					)}
					{error && <div style={{ fontSize: 11, color: "var(--danger)" }}>{error}</div>}
				</div>
				<button
					onClick={() => void handleLoad()}
					disabled={loading || downloaded}
					aria-label={`Download ${attachmentName || "file"}`}
					style={{
						flexShrink: 0,
						fontSize: 11,
						fontFamily: "var(--font-mono)",
						color: "var(--accent)",
						background: "var(--accent-soft)",
						border: "1px solid var(--border)",
						borderRadius: "var(--r-btn)",
						padding: "5px 10px",
						cursor: loading || downloaded ? "default" : "pointer",
						opacity: loading ? 0.6 : 1,
					}}
				>
					{loading ? "…" : downloaded ? "Downloaded" : "Download"}
				</button>
			</div>
		)
	}

	return (
		<div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 8 }}>
			<button
				onClick={() => void handleLoad()}
				disabled={loading}
				style={{
					fontSize: 12,
					fontFamily: "var(--font-mono)",
					color: "var(--accent)",
					background: "var(--accent-soft)",
					border: "1px solid var(--border)",
					borderRadius: "var(--r-btn)",
					padding: "5px 10px",
					cursor: loading ? "default" : "pointer",
					opacity: loading ? 0.6 : 1,
				}}
			>
				{loading ? "Loading…" : attachmentType === "image" ? "Show image" : "Show video"}
			</button>
			{error && <span style={{ fontSize: 12, color: "var(--danger)" }}>{error}</span>}
		</div>
	)
}
