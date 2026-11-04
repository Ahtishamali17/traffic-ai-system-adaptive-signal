import { LuTrafficCone } from 'react-icons/lu'

const PHASE_STYLES = {
  green: { dot: 'bg-signal-safe', text: 'text-signal-safe', border: 'border-signal-safe/40' },
  yellow: { dot: 'bg-signal-amber', text: 'text-signal-amber', border: 'border-signal-amber/40' },
  red: { dot: 'bg-signal-danger', text: 'text-signal-danger', border: 'border-signal-danger/40' },
}

/**
 * Displays live adaptive-signal status: one card per lane, showing its
 * current phase (green/yellow/red), remaining seconds if it's the active
 * green lane, and its current measured vehicle density. Polled from
 * GET /detection/sessions/{id}/signals by the parent page.
 */
export default function SignalPanel({ status }) {
  if (!status) return null

  return (
    <div className="glass-panel p-5">
      <div className="flex items-center gap-2 mb-4">
        <LuTrafficCone className="text-signal-amber" size={16} />
        <span className="eyebrow">Adaptive Signal Control</span>
        <span className="ml-auto font-mono text-[10px] text-ink-faint">cycle #{status.cycle_count}</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {status.lanes.map((lane) => {
          const style = PHASE_STYLES[lane.phase] || PHASE_STYLES.red
          const isActive = lane.lane_name === status.active_lane
          return (
            <div
              key={lane.lane_name}
              className={`rounded-lg border px-3 py-3 bg-panel-raised ${style.border} ${
                isActive ? 'ring-1 ring-offset-0' : 'opacity-70'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium capitalize">{lane.lane_name}</span>
                <span className={`w-2 h-2 rounded-full ${style.dot} ${lane.phase === 'green' ? 'animate-pulse' : ''}`} />
              </div>
              <p className={`font-mono text-xs mt-1 ${style.text} uppercase`}>
                {lane.phase}
                {lane.phase === 'green' && ` · ${lane.remaining_seconds.toFixed(0)}s left`}
              </p>
              <p className="font-mono text-[11px] text-ink-muted mt-1">density: {lane.current_density.toFixed(1)}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
