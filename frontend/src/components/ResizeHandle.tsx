"use client"

import { useCallback, useRef } from "react"

type Props = {
	onResize: (deltaX: number) => void
	ariaLabel: string
}

// A thin draggable strip between two columns. Reports pointer-move deltas to the
// parent (which owns the actual width state / clamping) rather than a final width,
// so it works the same regardless of which side's width the parent adjusts.
export function ResizeHandle({ onResize, ariaLabel }: Props) {
	const draggingRef = useRef(false)
	const lastXRef = useRef(0)
	const onResizeRef = useRef(onResize)
	onResizeRef.current = onResize

	const handlePointerMove = useCallback((e: PointerEvent) => {
		if (!draggingRef.current) return
		const delta = e.clientX - lastXRef.current
		lastXRef.current = e.clientX
		onResizeRef.current(delta)
	}, [])

	const stopDragging = useCallback(() => {
		draggingRef.current = false
		window.removeEventListener("pointermove", handlePointerMove)
		window.removeEventListener("pointerup", stopDragging)
		document.body.style.cursor = ""
		document.body.style.userSelect = ""
	}, [handlePointerMove])

	const startDragging = useCallback((e: React.PointerEvent) => {
		e.preventDefault()
		draggingRef.current = true
		lastXRef.current = e.clientX
		window.addEventListener("pointermove", handlePointerMove)
		window.addEventListener("pointerup", stopDragging)
		document.body.style.cursor = "col-resize"
		document.body.style.userSelect = "none"
	}, [handlePointerMove, stopDragging])

	return (
		<div
			role="separator"
			aria-label={ariaLabel}
			aria-orientation="vertical"
			onPointerDown={startDragging}
			className="resize-handle"
			style={{
				width: 5,
				flexShrink: 0,
				cursor: "col-resize",
				position: "relative",
				zIndex: 5,
			}}
		>
			<div
				aria-hidden="true"
				style={{
					position: "absolute",
					top: 0,
					bottom: 0,
					left: 2,
					width: 1,
					background: "var(--border)",
				}}
			/>
		</div>
	)
}
