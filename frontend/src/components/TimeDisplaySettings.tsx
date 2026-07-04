"use client"

import { useEffect, useMemo, useState } from "react"

import { HourCycle, listSupportedTimezones, loadTimePrefs, saveTimePrefs, TimePrefs } from "../lib/timePrefs"

export function TimeDisplaySettings() {
	const [prefs, setPrefs] = useState<TimePrefs | null>(null)
	const timezones = useMemo(() => listSupportedTimezones(), [])

	useEffect(() => {
		setPrefs(loadTimePrefs())
	}, [])

	function update(next: Partial<TimePrefs>) {
		setPrefs((prev) => {
			if (!prev) return prev
			const merged = { ...prev, ...next }
			saveTimePrefs(merged)
			return merged
		})
	}

	if (!prefs) return null

	return (
		<div
			style={{
				border: "1px solid var(--border)",
				borderRadius: "var(--r-card)",
				background: "var(--surface)",
				padding: "14px 16px",
				marginBottom: 16,
			}}
		>
			<div
				style={{
					fontSize: 10,
					fontFamily: "var(--font-mono)",
					color: "var(--text-3)",
					textTransform: "uppercase",
					letterSpacing: "0.08em",
					marginBottom: 8,
				}}
			>
				Time Display
			</div>

			<p style={{ fontSize: 12, color: "var(--text-2)", margin: "0 0 12px" }}>
				Controls how message timestamps are shown across the app. Your timezone is set here manually
				rather than detected from this device, since your OS clock may not match where you actually work.
				In Rocket.Chat direct messages, the other person&apos;s local time is shown too, when Rocket.Chat
				reports it.
			</p>

			<div style={{ display: "grid", gap: 10, maxWidth: 420 }}>
				<div>
					<label htmlFor="settings-my-timezone" style={{ fontSize: 11, color: "var(--text-3)", display: "block", marginBottom: 4 }}>
						My timezone
					</label>
					<select
						id="settings-my-timezone"
						value={prefs.myTimezone}
						onChange={(e) => update({ myTimezone: e.target.value })}
						style={{
							width: "100%",
							boxSizing: "border-box",
							padding: "8px 10px",
							border: "1px solid var(--border)",
							borderRadius: "var(--r-btn)",
							background: "var(--bg)",
							color: "var(--text)",
							fontSize: 13,
							fontFamily: "var(--font-mono)",
							outline: "none",
						}}
					>
						{!timezones.includes(prefs.myTimezone) && <option value={prefs.myTimezone}>{prefs.myTimezone}</option>}
						{timezones.map((tz) => (
							<option key={tz} value={tz}>
								{tz}
							</option>
						))}
					</select>
				</div>

				<div>
					<span style={{ fontSize: 11, color: "var(--text-3)", display: "block", marginBottom: 4 }}>Time format</span>
					<div style={{ display: "flex", gap: 8 }}>
						{(["24h", "12h"] as HourCycle[]).map((option) => (
							<button
								key={option}
								onClick={() => update({ hourCycle: option })}
								aria-pressed={prefs.hourCycle === option}
								style={{
									padding: "6px 14px",
									background: prefs.hourCycle === option ? "var(--accent)" : "transparent",
									color: prefs.hourCycle === option ? "var(--accent-fg)" : "var(--text-2)",
									border: "1px solid var(--border)",
									borderRadius: "var(--r-btn)",
									fontSize: 13,
									fontFamily: "var(--font-ui)",
									fontWeight: 500,
									cursor: "pointer",
								}}
							>
								{option === "24h" ? "24-hour" : "12-hour"}
							</button>
						))}
					</div>
				</div>

				<label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-2)", cursor: "pointer" }}>
					<input
						type="checkbox"
						checked={prefs.showUtc}
						onChange={(e) => update({ showUtc: e.target.checked })}
					/>
					Also show UTC time
				</label>
			</div>
		</div>
	)
}
