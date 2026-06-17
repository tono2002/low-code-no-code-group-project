import { useEffect, useRef } from 'react'

export default function CursorGlow() {
  const ref = useRef(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    let fx = 0, fy = 0, tx = 0, ty = 0, raf

    const onMove = e => { tx = e.clientX; ty = e.clientY }
    window.addEventListener('mousemove', onMove)

    const tick = () => {
      fx += (tx - fx) * 0.1
      fy += (ty - fy) * 0.1
      el.style.left = fx + 'px'
      el.style.top = fy + 'px'
      raf = requestAnimationFrame(tick)
    }
    tick()

    return () => {
      window.removeEventListener('mousemove', onMove)
      cancelAnimationFrame(raf)
    }
  }, [])

  return <div ref={ref} className="cursor-glow" aria-hidden="true" />
}
