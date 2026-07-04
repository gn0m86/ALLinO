type Props = {
	mode: "normal" | "focus" | "incident"
	onModeChange: (mode: "normal" | "focus" | "incident") => void
}

export function ModeToggle({ mode, onModeChange }: Props) {
	return (
		<div style={{ display: "flex", gap: 8 }}>
			<button onClick={() => onModeChange("normal")} disabled={mode === "normal"}>
				Normal
			</button>
			<button onClick={() => onModeChange("focus")} disabled={mode === "focus"}>
				Focus
			</button>
			<button
				onClick={() => onModeChange("incident")}
				disabled={mode === "incident"}
			>
				Incident
			</button>
		</div>
	)
}
