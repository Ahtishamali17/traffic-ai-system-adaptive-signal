import { useEffect, useState } from 'react'
import { LuCar, LuGauge, LuTriangleAlert, LuTrendingUp } from 'react-icons/lu'
import TopBar from '../components/TopBar.jsx'
import StatCard from '../components/StatCard.jsx'
import { analyticsApi, detectionApi } from '../api/client.js'

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [sessions, setSessions] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [summaryRes, sessionsRes] = await Promise.all([
          analyticsApi.getSummary({ days: 7 }),
          detectionApi.listSessions(),
        ])
        if (!cancelled) {
          setSummary(summaryRes.data)
          setSessions(sessionsRes.data)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) setError('Could not reach the backend API. Is it running?')
      }
    }

    load()
    const interval = setInterval(load, 10000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  return (
    <>
      <TopBar title="Dashboard" subtitle="Last 7 days across all cameras" />
      <div className="p-6 space-y-6">
        {error && (
          <div className="glass-panel border-signal-danger/30 p-4 text-signal-danger text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Vehicles This Week"
            value={summary?.total_vehicles ?? '—'}
            icon={LuCar}
            accent="amber"
            delay={0}
          />
          <StatCard
            label="Peak Hour"
            value={summary?.peak_hour?.hour?.split(' ')[1] ?? '—'}
            unit={summary?.peak_hour ? `${summary.peak_hour.count} vehicles` : ''}
            icon={LuTrendingUp}
            accent="safe"
            delay={0.05}
          />
          <StatCard
            label="Violations"
            value={summary?.total_violations ?? '—'}
            icon={LuTriangleAlert}
            accent="danger"
            delay={0.1}
          />
          <StatCard
            label="Active Sessions"
            value={sessions.filter((s) => s.status === 'running').length}
            icon={LuGauge}
            accent="default"
            delay={0.15}
          />
        </div>

        <div className="glass-panel p-5">
          <span className="eyebrow">Detection Sessions</span>
          <div className="mt-4 space-y-2">
            {sessions.length === 0 && (
              <p className="text-ink-muted text-sm py-8 text-center">
                No sessions yet. Start one from the Live Detection page.
              </p>
            )}
            {sessions.map((s) => (
              <div
                key={s.session_id}
                className="flex items-center justify-between px-4 py-3 rounded-lg bg-panel-raised border border-hairline"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      s.status === 'running'
                        ? 'bg-signal-safe animate-pulse'
                        : s.status === 'error'
                        ? 'bg-signal-danger'
                        : 'bg-ink-faint'
                    }`}
                  />
                  <span className="font-mono text-sm">{s.camera_id}</span>
                  <span className="text-ink-muted text-xs">{s.source_type}</span>
                </div>
                <div className="flex items-center gap-6 font-mono text-xs text-ink-muted">
                  <span>{s.total_frames_processed} frames</span>
                  <span>{s.current_fps} fps</span>
                  <span className="uppercase">{s.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {summary?.class_breakdown?.length > 0 && (
          <div className="glass-panel p-5">
            <span className="eyebrow">Vehicle Class Distribution</span>
            <div className="mt-4 space-y-3">
              {summary.class_breakdown.map((c) => (
                <div key={c.class_name} className="flex items-center gap-3">
                  <span className="text-sm w-32 capitalize text-ink-muted">
                    {c.class_name.replace('_', ' ')}
                  </span>
                  <div className="flex-1 h-2 bg-panel-raised rounded-full overflow-hidden">
                    <div
                      className="h-full bg-signal-amber rounded-full"
                      style={{ width: `${c.percentage}%` }}
                    />
                  </div>
                  <span className="font-mono text-xs text-ink-muted w-16 text-right">
                    {c.percentage}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  )
}
