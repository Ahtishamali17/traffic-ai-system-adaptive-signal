import { useState } from 'react'
import TopBar from '../components/TopBar.jsx'

const SETTING_GROUPS = [
  {
    title: 'Detection',
    fields: [
      { label: 'Confidence Threshold', value: '0.40', hint: 'Minimum detection confidence (0.05-0.95)' },
      { label: 'Frame Skip', value: '1', hint: 'Process every Nth frame' },
      { label: 'Device', value: 'CPU', hint: 'CPU, CUDA, or MPS' },
    ],
  },
  {
    title: 'Speed & Calibration',
    fields: [
      { label: 'Pixels per Meter', value: '8.0', hint: 'Camera-specific calibration constant' },
      { label: 'Speed Limit', value: '60 km/h', hint: 'Overspeed alert threshold' },
    ],
  },
  {
    title: 'Alerts',
    fields: [
      { label: 'Telegram Bot Token', value: 'Not configured', hint: 'Set via TELEGRAM_BOT_TOKEN env var' },
      { label: 'Alert Email', value: 'Not configured', hint: 'Set via ALERT_EMAIL_TO env var' },
      { label: 'Crowd Threshold', value: '15 vehicles', hint: 'Vehicles per frame that triggers a crowd alert' },
    ],
  },
]

export default function Settings() {
  const [saved, setSaved] = useState(false)

  return (
    <>
      <TopBar title="Settings" subtitle="Configuration reference - edit via backend/.env" />
      <div className="p-6 space-y-6 max-w-2xl">
        <div className="glass-panel border-signal-amber/20 p-4 text-sm text-ink-muted">
          These values are currently sourced from <code className="font-mono text-signal-amber">backend/.env</code> and
          passed per-session via the Live Detection start form. Live in-app editing of persisted settings ships in a
          future update.
        </div>

        {SETTING_GROUPS.map((group) => (
          <div key={group.title} className="glass-panel p-5">
            <span className="eyebrow">{group.title}</span>
            <div className="mt-4 space-y-4">
              {group.fields.map((f) => (
                <div key={f.label} className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm">{f.label}</p>
                    <p className="text-ink-faint text-xs mt-0.5">{f.hint}</p>
                  </div>
                  <span className="font-mono text-sm text-ink-muted shrink-0">{f.value}</span>
                </div>
              ))}
            </div>
          </div>
        ))}

        <button onClick={() => setSaved(true)} className="btn-primary">
          {saved ? 'Saved (local only)' : 'Save Changes'}
        </button>
      </div>
    </>
  )
}
