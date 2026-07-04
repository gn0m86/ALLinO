"use client"

import { useEffect, useRef, useState } from "react"

import { searchMessages } from "../lib/api"
import { InboxMessage } from "../lib/types"
import { InboxList } from "./InboxList"

type Props = {
	selectedId: string | null
	onSelect: (item: InboxMessage) => void
}

const DEBOUNCE_MS = 300

export function SearchPanel({ selectedId, onSelect }: Props) {
	const [query, setQuery] = useState("")
	const [results, setResults] = useState<InboxMessage[]>([])
	const [loading, setLoading] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [searched, setSearched] = useState(false)
	const debounceRef = useRef<number | null>(null)
	const abortRef = useRef<AbortController | null>(null)
	const disposedRef = useRef(false)

	useEffect(() => {
		disposedRef.current = false
		return () => {
			disposedRef.current = true
			if (debounceRef.current !== null) window.clearTimeout(debounceRef.current)
			abortRef.current?.abort()
		}
	}, [])

	useEffect(() => {
		if (debounceRef.current !== null) window.clearTimeout(debounceRef.current)
		abortRef.current?.abort()

		const trimmed = query.trim()
		if (!trimmed) {
			setResults([])
			setSearched(false)
			setLoading(false)
			setError(null)
			return
		}

		debounceRef.current = window.setTimeout(() => {
			const controller = new AbortController()
			abortRef.current = controller
			setLoading(true)
			setError(null)
			searchMessages(trimmed, controller.signal)
				.then((data) => {
					if (disposedRef.current) return
					setResults(data)
					setSearched(true)
				})
				.catch((e: unknown) => {
					if (e instanceof DOMException && e.name === "AbortError") return
					if (disposedRef.current) return
					setError(e instanceof Error ? e.message : "Search failed")
				})
				.finally(() => {
					if (!disposedRef.current) setLoading(false)
				})
		}, DEBOUNCE_MS)
	}, [query])

	return (
		<>
			<div style={{ padding: "10px 12px", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
				<input
					autoFocus
					value={query}
					onChange={(e) => setQuery(e.target.value)}
					placeholder="Search messages…"
					aria-label="Search messages"
					style={{
						width: "100%",
						boxSizing: "border-box",
						padding: "8px 10px",
						border: "1px solid var(--border)",
						borderRadius: "var(--r-btn)",
						background: "var(--bg)",
						color: "var(--text)",
						fontSize: 13,
						fontFamily: "var(--font-ui)",
						outline: "none",
					}}
				/>
			</div>
			<div style={{ flex: 1, overflowY: "auto" }}>
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
						Searching…
					</div>
				)}

				{!loading && error && (
					<div
						style={{
							margin: 12,
							padding: "10px 14px",
							background: "var(--danger-soft)",
							color: "var(--danger)",
							borderRadius: "var(--r-card)",
							fontSize: 13,
						}}
					>
						{error}
					</div>
				)}

				{!loading && !error && !searched && query.trim().length === 0 && (
					<div
						style={{
							padding: "32px 16px",
							textAlign: "center",
							color: "var(--text-3)",
							fontSize: 13,
							fontFamily: "var(--font-mono)",
						}}
					>
						Type to search your inbox.
					</div>
				)}

				{!loading && !error && searched && results.length === 0 && (
					<div
						style={{
							padding: "32px 16px",
							textAlign: "center",
							color: "var(--text-3)",
							fontSize: 13,
							fontFamily: "var(--font-mono)",
						}}
					>
						No matches for &ldquo;{query.trim()}&rdquo;.
					</div>
				)}

				{!loading && !error && results.length > 0 && (
					<InboxList items={results} selectedId={selectedId} onSelect={onSelect} />
				)}
			</div>
		</>
	)
}
