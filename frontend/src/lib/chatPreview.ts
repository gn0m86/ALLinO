import { InboxMessage } from "./types"

// Chat-shaped sources build `preview` as "{channel} | {sender} | {content}" (see
// each connector's map_*_to_unified_event). Their external_id is a technical
// "{room}:{message_id}" composite -- not something a person should have to read
// as a title. For these sources, split the channel name back out of preview
// instead of showing the raw external_id.
const CHAT_SOURCES = new Set(["rocketchat", "slack", "discord", "telegram", "teams"])

function splitChatPreview(preview: string): { channel: string; rest: string } | null {
	const idx = preview.indexOf(" | ")
	if (idx === -1) return null
	const channel = preview.slice(0, idx).trim()
	if (!channel) return null
	return { channel, rest: preview.slice(idx + 3) }
}

export function getDisplayTitle(item: InboxMessage): string {
	if (CHAT_SOURCES.has(item.source.toLowerCase())) {
		const split = splitChatPreview(item.preview || "")
		if (split) return split.channel
	}
	return item.external_id
}

export function getDisplayPreview(item: InboxMessage): string {
	if (CHAT_SOURCES.has(item.source.toLowerCase())) {
		const split = splitChatPreview(item.preview || "")
		if (split) return split.rest
	}
	return item.preview || ""
}

// For the chat-transcript view: split getDisplayPreview's "{sender} | {content}"
// (chat-shaped sources only) into the two parts a message bubble actually wants
// to show separately.
export function getDisplaySender(item: InboxMessage): string {
	const rest = getDisplayPreview(item)
	const idx = rest.indexOf(" | ")
	return idx === -1 ? "" : rest.slice(0, idx).trim()
}

export function getDisplayBody(item: InboxMessage): string {
	const rest = getDisplayPreview(item)
	const idx = rest.indexOf(" | ")
	return idx === -1 ? rest : rest.slice(idx + 3)
}

const AVATAR_COLOR_COUNT = 6

// A stable hash-based color per contact/channel name -- the same name always
// gets the same avatar color across renders and sessions without needing
// anything stored server-side (the same trick Slack/Rocket.Chat's own avatars
// use). Shared between ChannelBrowser's list rows and ChannelTranscript's header
// so the same contact/channel always shows the same color in both places.
export function avatarColorVar(seed: string): string {
	let hash = 0
	for (let i = 0; i < seed.length; i++) {
		hash = (hash * 31 + seed.charCodeAt(i)) | 0
	}
	const index = (Math.abs(hash) % AVATAR_COLOR_COUNT) + 1
	return `var(--avatar-${index})`
}
