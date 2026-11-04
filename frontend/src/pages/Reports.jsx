import { useState } from 'react'
import { LuFileText, LuSheet, LuFileDown } from 'react-icons/lu'
import TopBar from '../components/TopBar.jsx'
import { reportsApi } from '../api/client.js'

const REPORT_TYPES = [
  { key: 'csv', label: 'CSV', desc: 'Daily vehicle counts, spreadsheet-ready', icon: LuFileText, urlFn: reportsApi.csvUrl },
  { key: 'excel', label: 'Excel', desc: 'Multi-sheet workbook: daily, hourly, class, violations', icon: LuSheet, urlFn: reportsApi.excelUrl },
  { key: 'pdf', label: 'PDF', desc: 'Formatted summary report for sharing/printing', icon: LuFileDown, urlFn: reportsApi.pdfUrl },
]

export default function Reports() {
  const [days, setDays] = useState(7)
  const [cameraId, setCameraId] = useState('')

  function download(urlFn) {
    const params = { days: String(days), ...(cameraId ? { camera_id: cameraId } : {}) }
    window.open(urlFn(params), '_blank')
  }

  return (
    <>
      <TopBar title="Reports" subtitle="Export traffic data as CSV, Excel, or PDF" />
      <div className="p-6 space-y-6 max-w-3xl">
        <div className="glass-panel p-5 flex flex-wrap items-end gap-4">
          <div>
            <label className="text-xs text-ink-muted block mb-1.5">Period (days)</label>
            <input
              type="number"
              min={1}
              max={90}
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-28 bg-panel-raised border border-hairline rounded-lg px-3 py-2 text-sm font-mono"
            />
          </div>
          <div>
            <label className="text-xs text-ink-muted block mb-1.5">Camera ID (optional)</label>
            <input
              value={cameraId}
              onChange={(e) => setCameraId(e.target.value)}
              placeholder="All cameras"
              className="w-48 bg-panel-raised border border-hairline rounded-lg px-3 py-2 text-sm font-mono"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {REPORT_TYPES.map(({ key, label, desc, icon: Icon, urlFn }) => (
            <button
              key={key}
              onClick={() => download(urlFn)}
              className="glass-panel p-5 text-left hover:border-signal-amber/40 transition-colors group"
            >
              <Icon className="text-signal-amber mb-3" size={22} />
              <h3 className="font-display font-semibold">{label}</h3>
              <p className="text-ink-muted text-xs mt-1 leading-relaxed">{desc}</p>
              <span className="text-signal-amber text-xs font-mono mt-3 inline-block group-hover:underline">
                Download →
              </span>
            </button>
          ))}
        </div>
      </div>
    </>
  )
}
