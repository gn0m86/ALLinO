"use client"

import { useEffect, useState } from "react"

import { sendReply } from "../lib/api"
import { InboxMessage, REPLY_SUPPORTED_SOURCES } from "../lib/types"
import { SendIcon, ShieldCheck } from "./Icons"

type Props = {
	item: InboxMessage
	sourceLabel: string
}

export function ReplyComposer({ item, sourceLabel }: Props) {
	const [text, setText] = useState("")
	const [sending, setSending] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [sent, setSent] = useState(false)

	useEffect(() => {
		setText("")
		setSending(false)
		setError(null)
		setSent(false)
	}, [item.event_id])

	const canReply = (REPLY_SUPPORTED_SOURCES as readonly string[]).includes(item.source.toLowerCase())

	if (!canReply) {
		return (
			<div
				style={{
					borderTop: "1px solid var(--border)",
					padding: 12,
					background: "var(--surface)",
					flexShrink: 0,
				}}
			>
				<div
					style={{
						border: "1px solid var(--border)",
						borderRadius: "var(--r-card)",
						padding: "10px 12px",
						background: "var(--surface-2)",
						fontSize: 13,
						color: "var(--text-3)",
					}}
				>
					Replies aren&apos;t supported for {sourceLabel} yet.
				</div>
			</div>
		)
	}

	async function handleSend() {
		const trimmed = text.trim()
		if (!trimmed || sending) return
		setSending(true)
		setError(null)
		try {
			await sendReply(item.event_id, trimmed)
			setText("")
			setSent(true)
		} catch (e: unknown) {
			setError(e instanceof Error ? e.message : "Failed to send reply")
		} finally {
			setSending(false)
		}
	}

	return (
		<div
			style={{
				borderTop: "1px solid var(--border)",
				padding: 12,
				background: "var(--surface)",
				flexShrink: 0,
			}}
		>
			<div
				style={{
					border: "1px solid var(--border)",
					borderRadius: "var(--r-card)",
					padding: "10px 12px",
					background: "var(--bg)",
				}}
			>
				<textarea
					value={text}
					onChange={(e) => {
						setText(e.target.value)
						setSent(false)
					}}
					onKeyDown={(e) => {
						if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
							e.preventDefault()
							void handleSend()
						}
					}}
					placeholder="Reply…"
					rows={2}
					disabled={sending}
					aria-label="Reply message"
					style={{
						width: "100%",
						resize: "none",
						border: "none",
						outline: "none",
						background: "transparent",
						fontFamily: "var(--font-ui)",
						fontSize: 14,
						color: "var(--text)",
						marginBottom: 10,
					}}
				/>
				<div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
					<span
						style={{
							fontSize: 11,
							fontFamily: "var(--font-mono)",
							color: error ? "var(--danger)" : sent ? "var(--success)" : "var(--text-3)",
							display: "flex",
							alignItems: "center",
							gap: 4,
							minWidth: 0,
							overflow: "hidden",
							textOverflow: "ellipsis",
							whiteSpace: "nowrap",
						}}
					>
						<ShieldCheck size={11} />
						{error ? error : sent ? "Reply sent" : "Encrypted in transit (TLS)"}
					</span>
					<button
						onClick={() => void handleSend()}
						disabled={sending || !text.trim()}
						style={{
							display: "inline-flex",
							alignItems: "center",
							gap: 6,
							padding: "6px 14px",
							background: "var(--accent)",
							color: "var(--accent-fg)",
							border: "none",
							borderRadius: "var(--r-btn)",
							fontSize: 13,
							fontFamily: "var(--font-ui)",
							fontWeight: 500,
							cursor: sending || !text.trim() ? "default" : "pointer",
							opacity: sending || !text.trim() ? 0.6 : 1,
							flexShrink: 0,
						}}
					>
						<SendIcon size={13} />
						{sending ? "Sending…" : "Send"}
						<kbd
							style={{
								fontSize: 10,
								fontFamily: "var(--font-mono)",
								opacity: 0.6,
							}}
						>
							⌘↵
						</kbd>
					</button>
				</div>
			</div>
		</div>
	)
}
