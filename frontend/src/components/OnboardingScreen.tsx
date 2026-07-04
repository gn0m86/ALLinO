"use client"

type Props = {
	onGoToSettings: () => void
	onSkip: () => void
}

export function OnboardingScreen({ onGoToSettings, onSkip }: Props) {
	return (
		<div
			style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}
			role="region"
			aria-label="Onboarding"
		>
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
					Welcome to ALLinO
				</h2>
			</div>

			<div style={{ flex: 1, overflowY: "auto", padding: 20, maxWidth: 640 }}>
				<p style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.5, marginTop: 0 }}>
					Your unified inbox needs at least one connected source to show anything. Connect one
					now, or skip and connect it later from Settings — nothing here is blocked forever.
				</p>

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
						Built-in sources
					</div>
					<p style={{ fontSize: 12, color: "var(--text-2)", margin: "0 0 12px" }}>
						GitHub, GitLab, Jira, Linear, Telegram, Slack, Discord, Zoom, Teams, Google Calendar,
						Rocket.Chat. Each is configured via an environment variable on the backend — secrets
						are never entered through this UI, for security.
					</p>
					<button
						onClick={onGoToSettings}
						style={{
							fontSize: 11,
							fontFamily: "var(--font-mono)",
							color: "var(--accent)",
							background: "transparent",
							border: "1px solid var(--border)",
							borderRadius: "var(--r-btn)",
							padding: "6px 10px",
							cursor: "pointer",
						}}
					>
						View setup instructions
					</button>
				</div>

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
						Custom HTTP or webhook source
					</div>
					<p style={{ fontSize: 12, color: "var(--text-2)", margin: "0 0 12px" }}>
						Point ALLinO at any REST API, or receive events by webhook — no backend secret needed
						if you don't require auth.
					</p>
					<button
						onClick={onGoToSettings}
						style={{
							fontSize: 11,
							fontFamily: "var(--font-mono)",
							color: "var(--accent)",
							background: "transparent",
							border: "1px solid var(--border)",
							borderRadius: "var(--r-btn)",
							padding: "6px 10px",
							cursor: "pointer",
						}}
					>
						Create a custom connector
					</button>
				</div>

				<button
					onClick={onSkip}
					aria-label="Skip onboarding for now"
					style={{
						fontSize: 12,
						fontFamily: "var(--font-mono)",
						color: "var(--text-3)",
						background: "transparent",
						border: "none",
						padding: "4px 0",
						cursor: "pointer",
						textDecoration: "underline",
					}}
				>
					Skip for now
				</button>
			</div>
		</div>
	)
}
