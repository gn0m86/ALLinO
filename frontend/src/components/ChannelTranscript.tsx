"use client"

import { useEffect, useMemo, useRef, useState } from "react"

import { fetchRocketchatDmTimezone, fetchRocketchatOwnUsername, fetchThreadMessages, markThreadRead } from "../lib/api"
import { avatarColorVar, getDisplayBody, getDisplaySender, getDisplayTitle } from "../lib/chatPreview"
import { ChannelSummary, InboxMessage } from "../lib/types"
import { formatClockCluster, useTimePrefs } from "../lib/timePrefs"
import { AttachmentViewer } from "./AttachmentViewer"
import { ReplyComposer } from "./ReplyComposer"

type Props = {
	channel: ChannelSummary
}

const KIND_LABELS: Record<string, string> = {
	team: "Team",
	channel: "Channel",
	dm: "Direct message",
}

// Chat-transcript view: the full history of one channel/DM, oldest message at
// the top, newest at the bottom, matching Telegram/Rocket.Chat's own layout --
// scroll up for history, new messages arrive at the bottom.
export function ChannelTranscript({ channel }: Props) {
	const [messages, setMessages] = useState<InboxMessage[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)
	// Which message the composer replies to. Rocket.Chat's chat.postMessage
	// accepts a tmid (thread message id) -- every message's external_id carries
	// its own message id (see send_rocketchat_reply), so any message picked here
	// becomes a genuine threaded reply, not just a new message dropped in the
	// channel. Defaults to the channel's latest message until the user picks one.
	const [replyTarget, setReplyTarget] = useState<InboxMessage | null>(null)
	// The DM counterpart's UTC offset, when Rocket.Chat reports one -- only
	// meaningful for direct messages (see get_dm_counterpart_utc_offset), so this
	// stays null for channels/teams and the "them" clock is simply not shown.
	const [counterpartOffset, setCounterpartOffset] = useState<number | null>(null)
	// The configured account's own Rocket.Chat username -- lets "your" messages
	// always render in the app's accent color instead of a per-person hash color,
	// so they're recognizable at a glance no matter how many people are in a
	// channel. Fetched once; doesn't change per channel.
	const [ownUsername, setOwnUsername] = useState<string | null>(null)
	// The message currently flashed after clicking a "replying in thread" quote,
	// so jumping to the quoted message is easy to spot in a long transcript.
	const [highlightedId, setHighlightedId] = useState<string | null>(null)
	const timePrefs = useTimePrefs()
	const bottomRef = useRef<HTMLDivElement | null>(null)
	const messageRefs = useRef<Map<string, HTMLDivElement>>(new Map())

	useEffect(() => {
		const controller = new AbortController()
		fetchRocketchatOwnUsername(controller.signal)
			.then(setOwnUsername)
			.catch(() => undefined)
		return () => controller.abort()
	}, [])

	useEffect(() => {
		setCounterpartOffset(null)
		if (channel.channel_kind !== "dm") return
		const roomId = channel.latest.external_id.split(":")[0]
		if (!roomId) return

		const controller = new AbortController()
		fetchRocketchatDmTimezone(roomId, controller.signal)
			.then((offset) => setCounterpartOffset(offset))
			.catch(() => undefined)
		return () => controller.abort()
	}, [channel.thread_key, channel.channel_kind, channel.latest.external_id])

	useEffect(() => {
		let disposed = false
		const controller = new AbortController()
		setLoading(true)
		setError(null)
		setMessages([])
		setReplyTarget(null)

		fetchThreadMessages(channel.thread_key, controller.signal)
			.then((data) => {
				if (!disposed) setMessages(data)
			})
			.catch((e: unknown) => {
				if (e instanceof DOMException && e.name === "AbortError") return
				if (!disposed) setError(e instanceof Error ? e.message : "Failed to load conversation")
			})
			.finally(() => {
				if (!disposed) setLoading(false)
			})

		// Best-effort -- an unread badge lingering after a failed mark-as-read
		// call isn't worth surfacing as an error.
		markThreadRead(channel.thread_key).catch(() => undefined)

		return () => {
			disposed = true
			controller.abort()
		}
	}, [channel.thread_key])

	useEffect(() => {
		if (!loading) bottomRef.current?.scrollIntoView({ block: "end" })
	}, [loading, messages.length])

	const title = getDisplayTitle(channel.latest)
	const kindLabel = channel.channel_kind ? KIND_LABELS[channel.channel_kind] ?? "Channel" : "Channel"
	const effectiveReplyTarget = replyTarget ?? channel.latest
	const isChannelLike = channel.channel_kind === "channel" || channel.channel_kind === "team"
	const displayTitle = isChannelLike ? `#${title}` : title
	const initials = title.slice(0, 2).toUpperCase()
	const roomId = channel.latest.external_id.split(":")[0]

	// Rocket.Chat threads are flat (see the backend's reply_target docstring) --
	// every reply in a thread carries the thread ROOT's message id, not a chain
	// of individual reply pointers. Looked up against messages already loaded
	// for this same transcript, since the root is always in the same room/thread.
	const messagesByExternalId = useMemo(() => {
		const map = new Map<string, InboxMessage>()
		for (const m of messages) map.set(m.external_id, m)
		return map
	}, [messages])

	function scrollToMessage(eventId: string) {
		const el = messageRefs.current.get(eventId)
		if (!el) return
		el.scrollIntoView({ behavior: "smooth", block: "center" })
		setHighlightedId(eventId)
		window.setTimeout(() => setHighlightedId((prev) => (prev === eventId ? null : prev)), 1500)
	}

	return (
		<div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", height: "100%", background: "var(--bg)", overflow: "hidden" }}>
			<div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", flexShrink: 0, display: "flex", alignItems: "center", gap: 10 }}>
				<div
					style={{
						width: 32,
						height: 32,
						flexShrink: 0,
						borderRadius: "var(--r-card)",
						background: avatarColorVar(title),
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						fontSize: 12,
						fontWeight: 700,
						color: "#FFFFFF",
						fontFamily: "var(--font-ui)",
					}}
				>
					{initials}
				</div>
				<div style={{ minWidth: 0 }}>
					<div style={{ fontSize: 16.5, fontWeight: 600, fontFamily: "var(--font-head)", color: "var(--text)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
						{displayTitle}
					</div>
					<div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 1 }}>
						{kindLabel}
						{channel.channel_team ? ` · ${channel.channel_team}` : ""}
					</div>
				</div>
			</div>

			<div style={{ flex: 1, overflowY: "auto", padding: "12px 16px", display: "flex", flexDirection: "column", gap: 14 }}>
				{loading && (
					<div style={{ padding: "32px 0", textAlign: "center", color: "var(--text-3)", fontSize: 13, fontFamily: "var(--font-mono)" }}>
						Loading conversation…
					</div>
				)}
				{!loading && error && (
					<div style={{ padding: "10px 14px", background: "var(--danger-soft)", color: "var(--danger)", borderRadius: "var(--r-card)", fontSize: 13 }}>
						{error}
					</div>
				)}
				{!loading && !error && messages.length === 0 && (
					<div style={{ padding: "32px 0", textAlign: "center", color: "var(--text-3)", fontSize: 13, fontFamily: "var(--font-mono)" }}>
						No messages yet.
					</div>
				)}
				{!loading && !error && messages.map((m) => {
					const sender = getDisplaySender(m) || "?"
					const isOwn = Boolean(ownUsername) && sender.toLowerCase() === ownUsername!.toLowerCase()
					const senderColor = isOwn ? "var(--accent)" : avatarColorVar(sender)
					const threadRoot = m.reply_target ? messagesByExternalId.get(`${roomId}:${m.reply_target}`) : null
					const isSelfThread = threadRoot?.event_id === m.event_id
					return (
						<div
							key={m.event_id}
							ref={(el) => {
								if (el) messageRefs.current.set(m.event_id, el)
								else messageRefs.current.delete(m.event_id)
							}}
							style={{
								display: "flex",
								gap: 10,
								alignItems: "flex-start",
								borderRadius: "var(--r-card)",
								padding: 4,
								margin: -4,
								background: highlightedId === m.event_id ? "var(--accent-soft)" : "transparent",
								transition: "background 0.3s ease",
							}}
						>
							<div
								aria-hidden="true"
								style={{
									width: 30,
									height: 30,
									flexShrink: 0,
									borderRadius: "var(--r-card)",
									background: senderColor,
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									fontSize: 11,
									fontWeight: 700,
									color: "#FFFFFF",
									fontFamily: "var(--font-ui)",
								}}
							>
								{sender.slice(0, 2).toUpperCase()}
							</div>
							<div style={{ flex: 1, minWidth: 0 }}>
								<div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 3 }}>
									<span style={{ fontSize: 12, fontWeight: 700, color: senderColor }}>
										{sender}
										{isOwn && " (you)"}
									</span>
									<span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
										{formatClockCluster(m.timestamp, timePrefs, counterpartOffset)}
									</span>
									<button
										onClick={() => setReplyTarget(m)}
										aria-label={`Reply to ${sender}`}
										style={{
											marginLeft: "auto",
											fontSize: 11,
											fontFamily: "var(--font-mono)",
											color: m.event_id === effectiveReplyTarget.event_id ? "var(--accent)" : "var(--text-3)",
											fontWeight: m.event_id === effectiveReplyTarget.event_id ? 700 : 400,
											background: "transparent",
											border: "none",
											cursor: "pointer",
											padding: "2px 4px",
										}}
									>
										Reply
									</button>
								</div>
								{threadRoot && !isSelfThread && (
									<button
										onClick={() => scrollToMessage(threadRoot.event_id)}
										style={{
											display: "block",
											width: "100%",
											maxWidth: "62ch",
											textAlign: "left",
											marginBottom: 5,
											padding: "4px 8px",
											background: "var(--surface-2)",
											border: "none",
											borderLeft: `2px solid ${avatarColorVar(getDisplaySender(threadRoot) || "?")}`,
											borderRadius: "var(--r-chip)",
											cursor: "pointer",
											fontSize: 12,
											color: "var(--text-3)",
											overflow: "hidden",
											whiteSpace: "nowrap",
											textOverflow: "ellipsis",
										}}
									>
										↩ {getDisplaySender(threadRoot) || "?"}: {getDisplayBody(threadRoot) || "(no preview)"}
									</button>
								)}
								<p style={{ margin: 0, fontSize: 14, lineHeight: 1.5, color: "var(--text)", maxWidth: "62ch" }}>
									{getDisplayBody(m) || "(no preview)"}
								</p>
								{m.attachment_ref && m.attachment_type && (
									<AttachmentViewer eventId={m.event_id} attachmentType={m.attachment_type} attachmentName={m.attachment_name} attachmentSize={m.attachment_size} />
								)}
							</div>
						</div>
					)
				})}
				<div ref={bottomRef} />
			</div>

			{replyTarget && (
				<div
					style={{
						padding: "6px 16px",
						borderTop: "1px solid var(--border)",
						background: "var(--surface-2)",
						fontSize: 12,
						color: "var(--text-3)",
						display: "flex",
						alignItems: "center",
						gap: 8,
						flexShrink: 0,
					}}
				>
					<span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
						Replying to <strong style={{ color: "var(--text-2)" }}>{getDisplaySender(replyTarget) || "message"}</strong>
						{": "}
						{getDisplayBody(replyTarget) || "(no preview)"}
					</span>
					<button
						onClick={() => setReplyTarget(null)}
						style={{
							marginLeft: "auto",
							flexShrink: 0,
							fontSize: 11,
							fontFamily: "var(--font-mono)",
							color: "var(--accent)",
							background: "transparent",
							border: "none",
							cursor: "pointer",
							padding: "2px 4px",
						}}
					>
						Cancel
					</button>
				</div>
			)}
			<ReplyComposer item={effectiveReplyTarget} sourceLabel={channel.source} />
		</div>
	)
}
