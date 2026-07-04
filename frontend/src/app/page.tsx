"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import { ArchivedList } from "../components/ArchivedList"
import { ChannelBrowser } from "../components/ChannelBrowser"
import { ChannelTranscript } from "../components/ChannelTranscript"
import { DigestPanel } from "../components/DigestPanel"
import { FilterBar, FilterState } from "../components/FilterBar"
import { InboxList } from "../components/InboxList"
import { OnboardingScreen } from "../components/OnboardingScreen"
import { ResizeHandle } from "../components/ResizeHandle"
import { SearchPanel } from "../components/SearchPanel"
import { SecurityCenter } from "../components/SecurityCenter"
import { SettingsPanel } from "../components/SettingsPanel"
import { Sidebar } from "../components/Sidebar"
import { ThreadPanel } from "../components/ThreadPanel"
import { ArchiveIcon, ClockIcon, SearchIcon } from "../components/Icons"
import { fetchChannels, fetchConnectorCapabilities, fetchConnectorRuns, fetchConnectors, fetchInboxPage } from "../lib/api"
import {
	CHAT_SHAPED_SOURCES,
	ChannelSummary,
	ConnectorCapability,
	ConnectorRun,
	ConnectorStatus,
	InboxMessage,
	Mode,
	Priority,
} from "../lib/types"

const MODE_SESSION_KEY = "allino.mode"
const FILTERS_SESSION_KEY = "allino.filters"
const ONBOARDING_SKIPPED_STORAGE_KEY = "allino.onboarding.skipped"
const CONNECTORS_POLL_BASE_MS = 15000
const CONNECTORS_POLL_MAX_MS = 120000
const INBOX_POLL_MS = 20000
const CHANNELS_POLL_MS = 20000

const SIDEBAR_WIDTH_STORAGE_KEY = "allino.sidebarWidth"
const LIST_WIDTH_STORAGE_KEY = "allino.listWidth"
const SIDEBAR_WIDTH_DEFAULT = 218
const LIST_WIDTH_DEFAULT = 382
const SIDEBAR_WIDTH_MIN = 160
const SIDEBAR_WIDTH_MAX = 340
const LIST_WIDTH_MIN = 280
const LIST_WIDTH_MAX = 720

function clamp(value: number, min: number, max: number): number {
	return Math.min(Math.max(value, min), max)
}

const MODE_PRIORITY_FILTER: Partial<Record<Mode, Priority>> = {
	focus:    "high",
	incident: "high",
}

export default function HomePage() {
	const [items, setItems] = useState<InboxMessage[]>([])
	const [selected, setSelected] = useState<InboxMessage | null>(null)
	const [connectors, setConnectors] = useState<ConnectorStatus[]>([])
	const [connectorRuns, setConnectorRuns] = useState<ConnectorRun[]>([])
	const [connectorCapabilities, setConnectorCapabilities] = useState<ConnectorCapability[]>([])
	const [connectorsRefreshing, setConnectorsRefreshing] = useState(false)
	const [connectorsFailures, setConnectorsFailures] = useState(0)
	const [connectorsLastUpdatedAt, setConnectorsLastUpdatedAt] = useState<string | null>(null)
	// Initialized to the SSR-safe default here (never read sessionStorage during
	// the initial render) — a returning visitor's persisted mode/filters are
	// restored in a mount-only effect below, after hydration, to avoid a
	// server/client markup mismatch (React hydration error #418).
	const [mode, setMode] = useState<Mode>("normal")
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)
	const [filters, setFilters] = useState<FilterState>({ source: null, priority: null })
	const [showArchived, setShowArchived] = useState(false)
	const [searchOpen, setSearchOpen] = useState(false)
	const [digestOpen, setDigestOpen] = useState(false)
	const [channels, setChannels] = useState<ChannelSummary[]>([])
	const [channelsLoading, setChannelsLoading] = useState(false)
	const [channelsError, setChannelsError] = useState<string | null>(null)
	const [selectedChannel, setSelectedChannel] = useState<ChannelSummary | null>(null)
	// Which thing the right panel shows -- deliberately independent of
	// filters.source (which only controls the CENTER column's list vs.
	// channel-browser view). Without this, picking a specific message via Search
	// while filters.source happened to be "rocketchat" would leave the right
	// panel stuck showing a channel transcript instead of the message just
	// picked, since that panel used to key off filters.source directly.
	const [rightPanelMode, setRightPanelMode] = useState<"message" | "channel">("message")
	// SSR-safe defaults, restored from localStorage after mount (same pattern as
	// onboardingSkipped below) -- a user-chosen column width is a layout
	// preference, not session state, so it persists across browser restarts.
	const [sidebarWidth, setSidebarWidth] = useState(SIDEBAR_WIDTH_DEFAULT)
	const [listWidth, setListWidth] = useState(LIST_WIDTH_DEFAULT)
	// Same SSR-safe-default-then-restore-after-mount pattern as mode/filters below —
	// reading localStorage during the initial render would cause a hydration mismatch.
	const [onboardingSkipped, setOnboardingSkipped] = useState(false)
	const skipInitialModeReset = useRef(true)
	const restoringFromStorageRef = useRef(false)
	const connectorsTimerRef = useRef<number | null>(null)
	const connectorsAbortRef = useRef<AbortController | null>(null)
	const inboxTimerRef = useRef<number | null>(null)
	const inboxAbortRef = useRef<AbortController | null>(null)
	const inboxDisposedRef = useRef(false)
	const connectorsFailuresRef = useRef(0)
	const connectorsRefreshingRef = useRef(false)
	const connectorsDisposedRef = useRef(false)
	const channelsTimerRef = useRef<number | null>(null)
	const channelsAbortRef = useRef<AbortController | null>(null)
	const channelsDisposedRef = useRef(false)

	const mergeInboxItems = useCallback((prev: InboxMessage[], incoming: InboxMessage[]) => {
		const map = new Map<string, InboxMessage>()
		for (const item of prev) map.set(item.event_id, item)
		for (const item of incoming) map.set(item.event_id, item)
		return Array.from(map.values()).sort((a, b) => {
			const ta = new Date(a.timestamp).getTime()
			const tb = new Date(b.timestamp).getTime()
			if (tb !== ta) return tb - ta
			return b.event_id.localeCompare(a.event_id)
		})
	}, [])

	const clearConnectorsTimer = useCallback(() => {
		if (connectorsTimerRef.current !== null) {
			window.clearTimeout(connectorsTimerRef.current)
			connectorsTimerRef.current = null
		}
	}, [])

	const getNextConnectorsDelay = useCallback((failures: number) => {
		const delay = CONNECTORS_POLL_BASE_MS * (2 ** Math.min(failures, 3))
		return Math.min(delay, CONNECTORS_POLL_MAX_MS)
	}, [])

	const clearInboxTimer = useCallback(() => {
		if (inboxTimerRef.current !== null) {
			window.clearTimeout(inboxTimerRef.current)
			inboxTimerRef.current = null
		}
	}, [])

	const refreshInbox = useCallback(async () => {
		if (inboxDisposedRef.current) return

		clearInboxTimer()
		inboxAbortRef.current?.abort()
		const controller = new AbortController()
		inboxAbortRef.current = controller

		try {
			const page = await fetchInboxPage(120, null, controller.signal)
			if (inboxDisposedRef.current) return
			setItems((prev) => mergeInboxItems(prev, page.items))
			setError(null)
		} catch (e: unknown) {
			if (e instanceof DOMException && e.name === "AbortError") return
			if (inboxDisposedRef.current) return
			setError(e instanceof Error ? e.message : "Failed to load inbox")
		} finally {
			if (!inboxDisposedRef.current) {
				setLoading(false)
				inboxTimerRef.current = window.setTimeout(() => {
					void refreshInbox()
				}, INBOX_POLL_MS)
			}
		}
	}, [clearInboxTimer, mergeInboxItems])

	const refreshConnectors = useCallback(async (force = false) => {
		if (connectorsDisposedRef.current) return
		if (connectorsRefreshingRef.current && !force) return

		clearConnectorsTimer()
		connectorsAbortRef.current?.abort()
		const controller = new AbortController()
		connectorsAbortRef.current = controller

		connectorsRefreshingRef.current = true
		setConnectorsRefreshing(true)

		let nextDelay = CONNECTORS_POLL_BASE_MS
		try {
			const [statuses, runs, capabilities] = await Promise.all([
				fetchConnectors(controller.signal),
				fetchConnectorRuns(12, controller.signal),
				fetchConnectorCapabilities(controller.signal),
			])
			if (connectorsDisposedRef.current) return
			setConnectors(statuses)
			setConnectorRuns(runs)
			setConnectorCapabilities(capabilities)
			setConnectorsLastUpdatedAt(new Date().toISOString())
			connectorsFailuresRef.current = 0
			setConnectorsFailures(0)
			nextDelay = CONNECTORS_POLL_BASE_MS
		} catch (e: unknown) {
			if (e instanceof DOMException && e.name === "AbortError") return
			if (connectorsDisposedRef.current) return
			const nextFailures = connectorsFailuresRef.current + 1
			connectorsFailuresRef.current = nextFailures
			setConnectorsFailures(nextFailures)
			nextDelay = getNextConnectorsDelay(nextFailures)
		} finally {
			if (!connectorsDisposedRef.current) {
				connectorsRefreshingRef.current = false
				setConnectorsRefreshing(false)
				connectorsTimerRef.current = window.setTimeout(() => {
					void refreshConnectors()
				}, nextDelay)
			}
		}
	}, [clearConnectorsTimer, getNextConnectorsDelay])

	const clearChannelsTimer = useCallback(() => {
		if (channelsTimerRef.current !== null) {
			window.clearTimeout(channelsTimerRef.current)
			channelsTimerRef.current = null
		}
	}, [])

	const refreshChannels = useCallback(async (source: string) => {
		if (channelsDisposedRef.current) return

		clearChannelsTimer()
		channelsAbortRef.current?.abort()
		const controller = new AbortController()
		channelsAbortRef.current = controller

		try {
			const data = await fetchChannels(source, controller.signal)
			if (channelsDisposedRef.current) return
			setChannels(data)
			setChannelsError(null)
		} catch (e: unknown) {
			if (e instanceof DOMException && e.name === "AbortError") return
			if (channelsDisposedRef.current) return
			setChannelsError(e instanceof Error ? e.message : "Failed to load channels")
		} finally {
			if (!channelsDisposedRef.current) {
				setChannelsLoading(false)
				channelsTimerRef.current = window.setTimeout(() => {
					void refreshChannels(source)
				}, CHANNELS_POLL_MS)
			}
		}
	}, [clearChannelsTimer])

	useEffect(() => {
		inboxDisposedRef.current = false
		void refreshInbox()

		return () => {
			inboxDisposedRef.current = true
			clearInboxTimer()
			inboxAbortRef.current?.abort()
		}
	}, [clearInboxTimer, refreshInbox])

	useEffect(() => {
		connectorsDisposedRef.current = false
		void refreshConnectors(true)

		return () => {
			connectorsDisposedRef.current = true
			clearConnectorsTimer()
			connectorsAbortRef.current?.abort()
		}
	}, [clearConnectorsTimer, refreshConnectors])

	const handleRefreshConnectors = useCallback(() => {
		void refreshConnectors(true)
	}, [refreshConnectors])

	// Chat-shaped sources (currently just rocketchat) group by channel instead of
	// showing one row per message -- see chatPreview.ts / ChannelBrowser / ChannelTranscript.
	const chatSourceFilter = useMemo(() => {
		if (!filters.source) return null
		return (CHAT_SHAPED_SOURCES as readonly string[]).includes(filters.source) ? filters.source : null
	}, [filters.source])

	useEffect(() => {
		channelsDisposedRef.current = false

		if (!chatSourceFilter) {
			clearChannelsTimer()
			channelsAbortRef.current?.abort()
			setChannels([])
			setChannelsError(null)
			setChannelsLoading(false)
			setSelectedChannel(null)
			setRightPanelMode("message")
			return
		}

		setChannelsLoading(true)
		setSelectedChannel(null)
		void refreshChannels(chatSourceFilter)

		return () => {
			channelsDisposedRef.current = true
			clearChannelsTimer()
			channelsAbortRef.current?.abort()
		}
	}, [chatSourceFilter, clearChannelsTimer, refreshChannels])

	const handleSelectChannel = useCallback((channel: ChannelSummary) => {
		setSelectedChannel(channel)
		setRightPanelMode("channel")
		setChannels((prev) =>
			prev.map((c) => (c.thread_key === channel.thread_key ? { ...c, unread: false } : c)),
		)
	}, [])

	const handleSelectMessage = useCallback((item: InboxMessage) => {
		setSelected(item)
		setRightPanelMode("message")
	}, [])

	// Archive/snooze themselves call the backend from within ThreadPanel (same
	// shape as the existing reply composer) — these callbacks only need to
	// reflect the already-successful action back into local state: drop the
	// message from the list (the backend inbox listing already excludes it) and
	// clear the selection if it was the open thread.
	const handleMessageRemoved = useCallback((eventId: string) => {
		setItems((prev) => prev.filter((i) => i.event_id !== eventId))
		setSelected((prev) => (prev?.event_id === eventId ? null : prev))
	}, [])

	// Restore persisted mode/filters after mount (post-hydration) — see the
	// comment on the useState defaults above for why this can't happen earlier.
	// If a non-default mode is restored, mark it so the mode-change effect below
	// (which normally resets filters on every mode change) skips that one
	// resulting transition instead of clobbering the filters restored here.
	useEffect(() => {
		const rawFilters = window.sessionStorage.getItem(FILTERS_SESSION_KEY)
		if (rawFilters) {
			try {
				const parsed = JSON.parse(rawFilters) as Partial<FilterState>
				const source = typeof parsed.source === "string" ? parsed.source : null
				const priority =
					parsed.priority === "high" || parsed.priority === "medium" || parsed.priority === "normal"
						? parsed.priority
						: null
				setFilters({ source, priority })
			} catch {
				// ignore malformed persisted filters
			}
		}

		const rawMode = window.sessionStorage.getItem(MODE_SESSION_KEY)
		if (
			(rawMode === "focus" || rawMode === "incident" || rawMode === "security" || rawMode === "settings") &&
			rawMode !== mode
		) {
			restoringFromStorageRef.current = true
			setMode(rawMode)
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [])

	useEffect(() => {
		if (window.localStorage.getItem(ONBOARDING_SKIPPED_STORAGE_KEY) === "1") {
			setOnboardingSkipped(true)
		}
	}, [])

	useEffect(() => {
		const storedSidebar = Number(window.localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY))
		if (Number.isFinite(storedSidebar) && storedSidebar > 0) {
			setSidebarWidth(clamp(storedSidebar, SIDEBAR_WIDTH_MIN, SIDEBAR_WIDTH_MAX))
		}
		const storedList = Number(window.localStorage.getItem(LIST_WIDTH_STORAGE_KEY))
		if (Number.isFinite(storedList) && storedList > 0) {
			setListWidth(clamp(storedList, LIST_WIDTH_MIN, LIST_WIDTH_MAX))
		}
	}, [])

	useEffect(() => {
		window.localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(sidebarWidth))
	}, [sidebarWidth])

	useEffect(() => {
		window.localStorage.setItem(LIST_WIDTH_STORAGE_KEY, String(listWidth))
	}, [listWidth])

	const handleSidebarResize = useCallback((deltaX: number) => {
		setSidebarWidth((w) => clamp(w + deltaX, SIDEBAR_WIDTH_MIN, SIDEBAR_WIDTH_MAX))
	}, [])

	const handleListResize = useCallback((deltaX: number) => {
		setListWidth((w) => clamp(w + deltaX, LIST_WIDTH_MIN, LIST_WIDTH_MAX))
	}, [])

	const handleSkipOnboarding = useCallback(() => {
		window.localStorage.setItem(ONBOARDING_SKIPPED_STORAGE_KEY, "1")
		setOnboardingSkipped(true)
	}, [])

	const handleGoToSettingsFromOnboarding = useCallback(() => {
		setMode("settings")
	}, [])

	// When mode changes, reset manual filters and apply mode-based priority filter
	useEffect(() => {
		if (skipInitialModeReset.current) {
			skipInitialModeReset.current = false
			return
		}
		if (restoringFromStorageRef.current) {
			restoringFromStorageRef.current = false
			return
		}
		const modePriority = MODE_PRIORITY_FILTER[mode] ?? null
		setFilters({ source: null, priority: modePriority })
	}, [mode])

	useEffect(() => {
		window.sessionStorage.setItem(MODE_SESSION_KEY, mode)
	}, [mode])

	useEffect(() => {
		window.sessionStorage.setItem(FILTERS_SESSION_KEY, JSON.stringify(filters))
	}, [filters])

	const availableSources = useMemo(
		() => Array.from(new Set(items.map((i) => i.source))).sort(),
		[items],
	)

	const displayedItems = useMemo(() => {
		let result = items
		if (filters.source) result = result.filter((i) => i.source === filters.source)
		if (filters.priority) result = result.filter((i) => i.priority === filters.priority)
		return result
	}, [items, filters])

	const totalCount = items.length
	const filteredCount = displayedItems.length
	const isFiltered = filters.source !== null || filters.priority !== null

	const relatedItems = useMemo(() => {
		if (!selected) return []
		return items.filter(
			(i) => i.event_id !== selected.event_id && i.thread_key === selected.thread_key,
		)
	}, [items, selected])

	// Onboarding is required-but-skippable (PROJECT_MASTER_BRIEF.md §A.5): shown once
	// capabilities have actually loaded (avoids a flash before the first fetch resolves),
	// only while the inbox is genuinely empty and no built-in source is configured yet.
	// A registered-but-not-yet-synced Generic HTTP Connector won't suppress this screen —
	// deliberate simplification, see the Sprint 21 board — Skip or an arriving message
	// both resolve it.
	const capabilitiesLoaded = connectorsLastUpdatedAt !== null
	const hasConfiguredCapability = connectorCapabilities.some((c) => c.configured)
	const showOnboarding =
		mode === "normal" && !onboardingSkipped && capabilitiesLoaded && !loading && totalCount === 0 && !hasConfiguredCapability

	return (
		<main
			style={{
				display: "flex",
				height: "100vh",
				overflow: "hidden",
				background: "var(--bg)",
			}}
		>
			<Sidebar
				activeMode={mode}
				onModeChange={setMode}
				connectorCapabilities={connectorCapabilities}
				connectors={connectors}
				connectorRuns={connectorRuns}
				connectorsRefreshing={connectorsRefreshing}
				connectorsLastUpdatedAt={connectorsLastUpdatedAt}
				connectorsFailures={connectorsFailures}
				onRefreshConnectors={handleRefreshConnectors}
				width={sidebarWidth}
			/>
			<ResizeHandle ariaLabel="Resize navigation sidebar" onResize={handleSidebarResize} />

			{mode === "security" && <SecurityCenter />}
			{mode === "settings" && <SettingsPanel capabilities={connectorCapabilities} connectors={connectors} />}
			{showOnboarding && (
				<OnboardingScreen onGoToSettings={handleGoToSettingsFromOnboarding} onSkip={handleSkipOnboarding} />
			)}

			{mode !== "security" && mode !== "settings" && !showOnboarding && (
			<>
			{/* Message list column */}
			<section
				style={{
					width: listWidth,
					minWidth: listWidth,
					borderRight: "1px solid var(--border)",
					display: "flex",
					flexDirection: "column",
					overflow: "hidden",
					background: "var(--surface)",
				}}
			>
				{showArchived ? (
					<ArchivedList onClose={() => setShowArchived(false)} />
				) : searchOpen ? (
					<>
					<div
						style={{
							display: "flex",
							alignItems: "center",
							gap: 8,
							padding: "14px 16px",
							borderBottom: "1px solid var(--border)",
							flexShrink: 0,
						}}
					>
						<h2
							style={{
								margin: 0,
								flex: 1,
								fontSize: 15,
								fontWeight: "var(--head-weight)",
								fontFamily: "var(--font-head)",
								letterSpacing: "var(--head-tracking)",
								color: "var(--text)",
							}}
						>
							Search
						</h2>
						<button
							onClick={() => setSearchOpen(false)}
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
							Back to Inbox
						</button>
					</div>
					<SearchPanel
						selectedId={selected?.event_id ?? null}
						onSelect={(item) => {
							handleSelectMessage(item)
							setSearchOpen(false)
						}}
					/>
					</>
				) : digestOpen ? (
					<>
					<div
						style={{
							display: "flex",
							alignItems: "center",
							gap: 8,
							padding: "14px 16px",
							borderBottom: "1px solid var(--border)",
							flexShrink: 0,
						}}
					>
						<h2
							style={{
								margin: 0,
								flex: 1,
								fontSize: 15,
								fontWeight: "var(--head-weight)",
								fontFamily: "var(--font-head)",
								letterSpacing: "var(--head-tracking)",
								color: "var(--text)",
							}}
						>
							Digest
						</h2>
						<button
							onClick={() => setDigestOpen(false)}
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
							Back to Inbox
						</button>
					</div>
					<DigestPanel
						selectedId={selected?.event_id ?? null}
						onSelect={(item) => {
							handleSelectMessage(item)
							setDigestOpen(false)
						}}
					/>
					</>
				) : (
					<>
					{/* Column header */}
					<div
						style={{
							display: "flex",
							alignItems: "center",
							gap: 8,
							padding: "14px 16px",
							borderBottom: "1px solid var(--border)",
							flexShrink: 0,
						}}
					>
						<h2
							style={{
								margin: 0,
								flex: 1,
								fontSize: 15,
								fontWeight: "var(--head-weight)",
								fontFamily: "var(--font-head)",
								letterSpacing: "var(--head-tracking)",
								color: "var(--text)",
								display: "flex",
								alignItems: "center",
								gap: 8,
							}}
						>
							{mode === "normal" && "Inbox"}
							{mode === "focus" && "Focus Mode"}
							{mode === "incident" && "Incident"}
							{totalCount > 0 && (
								<span
									style={{
										fontSize: 11,
										fontFamily: "var(--font-mono)",
										background: isFiltered ? "var(--warning-soft)" : "var(--accent-soft)",
										color: isFiltered ? "var(--warning)" : "var(--accent)",
										borderRadius: 999,
										padding: "1px 7px",
									}}
								>
									{isFiltered ? `${filteredCount}/${totalCount}` : totalCount}
								</span>
							)}
						</h2>
						<button
							onClick={() => setShowArchived(true)}
							className="icon-btn"
							aria-label="View archived messages"
							title="View archived messages"
						>
							<ArchiveIcon size={14} />
						</button>
						<button
							onClick={() => setSearchOpen(true)}
							className="icon-btn"
							aria-label="Search"
							title="Search"
						>
							<SearchIcon size={14} />
						</button>
						<button
							onClick={() => setDigestOpen(true)}
							className="icon-btn"
							aria-label="Activity digest"
							title="Activity digest"
						>
							<ClockIcon size={14} />
						</button>
					</div>

					{/* Filter bar */}
					{!loading && !error && (
						<FilterBar
							filters={filters}
							availableSources={availableSources}
							onChange={setFilters}
						/>
					)}

					{/* Scrollable list */}
					<div style={{ flex: 1, overflowY: "auto" }}>
						{chatSourceFilter ? (
							<>
								{channelsLoading && channels.length === 0 && (
									<div
										style={{
											padding: "32px 16px",
											textAlign: "center",
											color: "var(--text-3)",
											fontSize: 13,
											fontFamily: "var(--font-mono)",
										}}
									>
										Loading channels…
									</div>
								)}
								{channelsError && (
									<div
										style={{
											margin: 12,
											padding: "10px 14px",
											background: "var(--danger-soft)",
											color: "var(--danger)",
											borderRadius: "var(--r-card)",
											fontSize: 13,
											display: "flex",
											alignItems: "flex-start",
											gap: 8,
										}}
									>
										<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: 1 }}>
											<circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
										</svg>
										<div>
											<div style={{ fontWeight: 600 }}>Failed to load channels</div>
											<div style={{ marginTop: 2, opacity: 0.8 }}>{channelsError} — We'll retry automatically.</div>
										</div>
									</div>
								)}
								{(!channelsLoading || channels.length > 0) && (
									<ChannelBrowser
										channels={channels}
										selectedThreadKey={selectedChannel?.thread_key ?? null}
										onSelect={handleSelectChannel}
									/>
								)}
							</>
						) : (
							<>
								{loading && (
									<div
										style={{
											padding: "32px 16px",
											textAlign: "center",
											color: "var(--text-3)",
											fontSize: 13,
											fontFamily: "var(--font-mono)",
										}}
									>
										Syncing sources…
									</div>
								)}
								{error && (
									<div
										style={{
											margin: 12,
											padding: "10px 14px",
											background: "var(--danger-soft)",
											color: "var(--danger)",
											borderRadius: "var(--r-card)",
											fontSize: 13,
											display: "flex",
											alignItems: "flex-start",
											gap: 8,
										}}
									>
										<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: 1 }}>
											<circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
										</svg>
										<div>
											<div style={{ fontWeight: 600 }}>Failed to load inbox</div>
											<div style={{ marginTop: 2, opacity: 0.8 }}>{error} — We'll retry automatically.</div>
										</div>
									</div>
								)}
								{!loading && !error && (
									<>
										{displayedItems.length === 0 && totalCount > 0 ? (
											<div
												style={{
													padding: "32px 16px",
													textAlign: "center",
													color: "var(--text-3)",
													fontSize: 13,
													fontFamily: "var(--font-mono)",
												}}
											>
												No messages match the current filters.
											</div>
										) : (
											<InboxList
												items={displayedItems}
												selectedId={selected?.event_id ?? null}
												onSelect={handleSelectMessage}
											/>
										)}
									</>
								)}
							</>
						)}
					</div>
					</>
				)}
			</section>
			<ResizeHandle ariaLabel="Resize message list" onResize={handleListResize} />

			{/* Thread panel */}
			<div style={{ flex: 1, minWidth: 0, overflow: "hidden", display: "flex" }}>
				{rightPanelMode === "channel" ? (
					selectedChannel ? (
						<ChannelTranscript channel={selectedChannel} />
					) : (
						<div
							style={{
								flex: 1,
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								color: "var(--text-3)",
								fontSize: 13,
								fontFamily: "var(--font-mono)",
								background: "var(--bg)",
							}}
						>
							Select a channel to open the conversation
						</div>
					)
				) : (
					<ThreadPanel
						item={selected}
						relatedItems={relatedItems}
						connectors={connectors}
						connectorRuns={connectorRuns}
						connectorsRefreshing={connectorsRefreshing}
						connectorsLastUpdatedAt={connectorsLastUpdatedAt}
						onArchived={handleMessageRemoved}
						onSnoozed={handleMessageRemoved}
						onSelectRelated={handleSelectMessage}
					/>
				)}
			</div>
			</>
			)}
		</main>
	)
}
