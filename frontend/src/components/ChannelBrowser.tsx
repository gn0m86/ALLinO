import { avatarColorVar, getDisplayPreview, getDisplayTitle } from "../lib/chatPreview"
import { ChannelSummary } from "../lib/types"

type Props = {
	channels: ChannelSummary[]
	selectedThreadKey: string | null
	onSelect: (channel: ChannelSummary) => void
}

function formatTime(ts: string): string {
	const d = new Date(ts)
	if (isNaN(d.getTime())) return ""
	const diff = Date.now() - d.getTime()
	const m = Math.floor(diff / 60000)
	if (m < 1) return "now"
	if (m < 60) return `${m}m`
	const h = Math.floor(m / 60)
	if (h < 24) return `${h}h`
	return `${Math.floor(h / 24)}d`
}

function SectionHeader({ label }: { label: string }) {
	return (
		<div
			style={{
				padding: "10px 12px 4px",
				fontSize: 10,
				fontFamily: "var(--font-mono)",
				color: "var(--text-3)",
				textTransform: "uppercase",
				letterSpacing: "0.08em",
			}}
		>
			{label}
		</div>
	)
}

function ChannelRow({
	channel,
	selected,
	onSelect,
}: {
	channel: ChannelSummary
	selected: boolean
	onSelect: () => void
}) {
	const title = getDisplayTitle(channel.latest)
	const preview = getDisplayPreview(channel.latest)
	const initials = title.slice(0, 2).toUpperCase()
	const isChannelLike = channel.channel_kind === "channel" || channel.channel_kind === "team"
	const displayTitle = isChannelLike ? `#${title}` : title

	return (
		<li role="listitem">
			<button
				className={`inbox-item${selected ? " selected" : ""}`}
				onClick={onSelect}
				aria-label={`${title}${channel.unread ? " (unread)" : ""}: ${preview || "no messages"}`}
				aria-pressed={selected}
			>
				<div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
					<div
						style={{
							width: 38,
							height: 38,
							flexShrink: 0,
							borderRadius: "var(--r-card)",
							background: avatarColorVar(title),
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							fontSize: 13,
							fontWeight: 700,
							color: "#FFFFFF",
							fontFamily: "var(--font-ui)",
						}}
					>
						{initials}
					</div>
					<div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 3 }}>
						<div style={{ display: "flex", alignItems: "center", gap: 6 }}>
							{channel.unread && (
								<span
									aria-hidden="true"
									style={{
										width: 7,
										height: 7,
										borderRadius: "50%",
										background: "var(--accent)",
										flexShrink: 0,
									}}
								/>
							)}
							<span
								style={{
									flex: 1,
									minWidth: 0,
									fontSize: 14,
									fontWeight: channel.unread ? 700 : 500,
									color: "var(--text)",
									whiteSpace: "nowrap",
									overflow: "hidden",
									textOverflow: "ellipsis",
								}}
							>
								{displayTitle}
							</span>
							<span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-3)", flexShrink: 0 }}>
								{formatTime(channel.latest.timestamp)}
							</span>
						</div>
						<div
							style={{
								fontSize: 13,
								color: channel.unread ? "var(--text-2)" : "var(--text-3)",
								whiteSpace: "nowrap",
								overflow: "hidden",
								textOverflow: "ellipsis",
							}}
						>
							{preview || "(no preview)"}
						</div>
					</div>
				</div>
			</button>
		</li>
	)
}

export function ChannelBrowser({ channels, selectedThreadKey, onSelect }: Props) {
	if (channels.length === 0) {
		return (
			<div style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
				No channels yet. Sync a chat source to see it here.
			</div>
		)
	}

	const teams = channels.filter((c) => c.channel_kind === "team")
	const regularChannels = channels.filter((c) => c.channel_kind === "channel")
	const dms = channels.filter((c) => c.channel_kind === "dm")

	return (
		<ul role="list" style={{ listStyle: "none", margin: 0, padding: "4px 8px 12px" }}>
			{teams.length > 0 && (
				<>
					<SectionHeader label="Teams" />
					{teams.map((c) => (
						<ChannelRow
							key={c.thread_key}
							channel={c}
							selected={c.thread_key === selectedThreadKey}
							onSelect={() => onSelect(c)}
						/>
					))}
				</>
			)}
			{regularChannels.length > 0 && (
				<>
					<SectionHeader label="Channels" />
					{regularChannels.map((c) => (
						<ChannelRow
							key={c.thread_key}
							channel={c}
							selected={c.thread_key === selectedThreadKey}
							onSelect={() => onSelect(c)}
						/>
					))}
				</>
			)}
			{dms.length > 0 && (
				<>
					<SectionHeader label="Direct messages" />
					{dms.map((c) => (
						<ChannelRow
							key={c.thread_key}
							channel={c}
							selected={c.thread_key === selectedThreadKey}
							onSelect={() => onSelect(c)}
						/>
					))}
				</>
			)}
		</ul>
	)
}
