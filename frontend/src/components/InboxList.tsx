import { getDisplayPreview, getDisplayTitle } from "../lib/chatPreview"
import { InboxMessage, Priority } from "../lib/types"

const PRIORITY_STYLES: Record<Priority, { color: string; bg: string; label: string }> = {
	high:   { color: "var(--c-red,#e53e3e)",    bg: "rgba(229,62,62,0.1)",   label: "!" },
	medium: { color: "var(--c-amber,#d97706)",  bg: "rgba(217,119,6,0.1)",   label: "~" },
	normal: { color: "var(--text-3)",            bg: "transparent",           label: ""  },
}

type Props = {
	items: InboxMessage[]
	selectedId: string | null
	onSelect: (item: InboxMessage) => void
}

const SOURCE_MAP: Record<string, { color: string; bg: string; abbr: string }> = {
	github:   { color: "var(--src-email)",    bg: "var(--src-email-soft)",    abbr: "GH" },
	gitlab:   { color: "var(--src-telegram)", bg: "var(--src-telegram-soft)", abbr: "GL" },
	linear:   { color: "var(--src-slack)",    bg: "var(--src-slack-soft)",    abbr: "LN" },
	slack:    { color: "var(--src-slack)",    bg: "var(--src-slack-soft)",    abbr: "#"  },
	telegram: { color: "var(--src-telegram)", bg: "var(--src-telegram-soft)", abbr: "TG" },
	email:    { color: "var(--src-email)",    bg: "var(--src-email-soft)",    abbr: "@"  },
}
const DEFAULT_SOURCE = { color: "var(--text-3)", bg: "var(--surface-3)", abbr: "•" }

function getSource(source: string) {
	return SOURCE_MAP[source.toLowerCase()] ?? DEFAULT_SOURCE
}

function getInitials(externalId: string): string {
	const parts = externalId.replace(/[#@/]/g, "-").split(/[-_]/).filter(Boolean)
	if (parts.length === 0) return "?"
	if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
	return (parts[0][0] + parts[1][0]).toUpperCase()
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

export function InboxList({ items, selectedId, onSelect }: Props) {
	if (items.length === 0) {
		return (
			<div
				style={{
					padding: "32px 16px",
					textAlign: "center",
					color: "var(--text-3)",
					fontSize: 13,
				}}
			>
				No messages yet. Ingest events to see inbox items.
			</div>
		)
	}

	return (
		<ul role="list" style={{ listStyle: "none", margin: 0, padding: "4px 8px" }}>
			{items.map((item) => {
				const src = getSource(item.source)
				const title = getDisplayTitle(item)
				const preview = getDisplayPreview(item)
				const initials = getInitials(title)
				const time = formatTime(item.timestamp)
				const isSelected = item.event_id === selectedId

				return (
					<li key={item.event_id} role="listitem">
						<button
							className={`inbox-item${isSelected ? " selected" : ""}`}
							onClick={() => onSelect(item)}
							aria-label={`${title}: ${preview || "no preview"}`}
							aria-pressed={isSelected}
						>
							<div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
								{/* Avatar block */}
								<div style={{ position: "relative", flexShrink: 0 }}>
									<div
										style={{
											width: 38,
											height: 38,
											borderRadius: "var(--r-card)",
											background: "var(--surface-3)",
											display: "flex",
											alignItems: "center",
											justifyContent: "center",
											fontSize: 13,
											fontWeight: 600,
											color: "var(--text-2)",
											fontFamily: "var(--font-ui)",
										}}
									>
										{initials}
									</div>
									{/* Source badge */}
									<div
										style={{
											position: "absolute",
											bottom: -2,
											right: -2,
											width: 17,
											height: 17,
											borderRadius: 6,
											background: src.bg,
											color: src.color,
											border: "2px solid var(--surface)",
											display: "flex",
											alignItems: "center",
											justifyContent: "center",
											fontSize: 7,
											fontFamily: "var(--font-mono)",
											fontWeight: 600,
										}}
									>
										{src.abbr.slice(0, 1)}
									</div>
								</div>

								{/* Body */}
								<div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 3 }}>
									{/* Line 1: sender + time */}
									<div style={{ display: "flex", alignItems: "center", gap: 4 }}>
										<span
											style={{
												flex: 1,
												minWidth: 0,
												fontSize: 14,
												fontWeight: 500,
												color: "var(--text)",
												whiteSpace: "nowrap",
												overflow: "hidden",
												textOverflow: "ellipsis",
											}}
										>
											{title}
										</span>
										{time && (
											<span
												style={{
													fontSize: 11,
													fontFamily: "var(--font-mono)",
													color: "var(--text-3)",
													flexShrink: 0,
												}}
											>
												{time}
											</span>
										)}
									</div>

									{/* Line 2: source chip + priority badge + preview as subject */}
									<div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
										<span
											style={{
												fontSize: 11,
												fontFamily: "var(--font-mono)",
												color: src.color,
												background: src.bg,
												borderRadius: 5,
												padding: "1px 5px",
												flexShrink: 0,
											}}
										>
											{item.source}
										</span>
										{item.priority !== "normal" && (
											<span
												style={{
													fontSize: 10,
													fontFamily: "var(--font-mono)",
													fontWeight: 700,
													color: PRIORITY_STYLES[item.priority].color,
													background: PRIORITY_STYLES[item.priority].bg,
													borderRadius: 4,
													padding: "1px 4px",
													flexShrink: 0,
												}}
											>
												{PRIORITY_STYLES[item.priority].label}
											</span>
										)}
										<span
											style={{
												fontSize: 14,
												fontWeight: 500,
												color: "var(--text)",
												whiteSpace: "nowrap",
												overflow: "hidden",
												textOverflow: "ellipsis",
											}}
										>
											{preview.slice(0, 60) || "(no preview)"}
										</span>
									</div>

									{/* Line 3: snippet */}
									{preview.length > 60 && (
										<div
											style={{
												fontSize: 13,
												color: "var(--text-2)",
												whiteSpace: "nowrap",
												overflow: "hidden",
												textOverflow: "ellipsis",
											}}
										>
											{preview.slice(60)}
										</div>
									)}
								</div>
							</div>
						</button>
					</li>
				)
			})}
		</ul>
	)
}
