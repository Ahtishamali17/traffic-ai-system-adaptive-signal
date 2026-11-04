import { useEffect, useState } from 'react'
import { Line, Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js'
import TopBar from '../components/TopBar.jsx'
import { analyticsApi } from '../api/client.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, ArcElement, Tooltip, Legend)

const CHART_COLORS = ['#F5A623', '#2DD4BF', '#E5484D', '#7C8798', '#8A5D14', '#4B5563']

const CHART_TEXT_COLOR = '#7C8798'
const CHART_GRID_COLOR = 'rgba(30,40,54,0.6)'

export default function Analytics() {
  const [days, setDays] = useState(7)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    analyticsApi
      .getSummary({ days })
      .then((res) => !cancelled && setSummary(res.data))
      .catch(() => !cancelled && setError('Could not load analytics data.'))
    return () => {
      cancelled = true
    }
  }, [days])

  const dailyChartData = {
    labels: summary?.daily_counts?.map((d) => d.date) ?? [],
    datasets: [
      {
        label: 'Vehicles per day',
        data: summary?.daily_counts?.map((d) => d.count) ?? [],
        borderColor: '#F5A623',
        backgroundColor: 'rgba(245,166,35,0.1)',
        fill: true,
        tension: 0.3,
      },
    ],
  }

  const hourlyChartData = {
    labels: summary?.hourly_counts?.map((h) => h.hour.split(' ')[1]) ?? [],
    datasets: [
      {
        label: 'Vehicles per hour',
        data: summary?.hourly_counts?.map((h) => h.count) ?? [],
        borderColor: '#2DD4BF',
        backgroundColor: 'rgba(45,212,191,0.1)',
        fill: true,
        tension: 0.3,
      },
    ],
  }

  const classChartData = {
    labels: summary?.class_breakdown?.map((c) => c.class_name.replace('_', ' ')) ?? [],
    datasets: [
      {
        data: summary?.class_breakdown?.map((c) => c.count) ?? [],
        backgroundColor: CHART_COLORS,
        borderColor: '#10151F',
        borderWidth: 2,
      },
    ],
  }

  const lineOptions = {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: CHART_TEXT_COLOR, font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: CHART_GRID_COLOR } },
      y: { ticks: { color: CHART_TEXT_COLOR, font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: CHART_GRID_COLOR } },
    },
  }

  return (
    <>
      <TopBar title="Analytics" subtitle="Traffic density and vehicle distribution" />
      <div className="p-6 space-y-6">
        <div className="flex items-center gap-2">
          {[1, 7, 30].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono border transition-colors ${
                days === d
                  ? 'border-signal-amber text-signal-amber bg-signal-amber/10'
                  : 'border-hairline text-ink-muted hover:text-ink-primary'
              }`}
            >
              {d === 1 ? 'Today' : `${d} Days`}
            </button>
          ))}
        </div>

        {error && <div className="glass-panel border-signal-danger/30 p-4 text-signal-danger text-sm">{error}</div>}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 glass-panel p-5">
            <span className="eyebrow">Daily Vehicle Count</span>
            <div className="mt-4 h-64">
              <Line data={dailyChartData} options={lineOptions} />
            </div>
          </div>

          <div className="glass-panel p-5">
            <span className="eyebrow">Vehicle Distribution</span>
            <div className="mt-4 h-64 flex items-center justify-center">
              {summary?.class_breakdown?.length ? (
                <Doughnut
                  data={classChartData}
                  options={{
                    plugins: {
                      legend: {
                        position: 'bottom',
                        labels: { color: CHART_TEXT_COLOR, font: { size: 10 }, boxWidth: 10 },
                      },
                    },
                  }}
                />
              ) : (
                <p className="text-ink-faint text-sm font-mono">No data yet</p>
              )}
            </div>
          </div>

          <div className="lg:col-span-2 glass-panel p-5">
            <span className="eyebrow">Hourly Traffic Density</span>
            <div className="mt-4 h-64">
              <Line data={hourlyChartData} options={lineOptions} />
            </div>
          </div>

          <div className="glass-panel p-5">
            <span className="eyebrow">Violations by Type</span>
            <div className="mt-4 space-y-3">
              {summary?.violations_by_type && Object.keys(summary.violations_by_type).length > 0 ? (
                Object.entries(summary.violations_by_type).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between text-sm">
                    <span className="text-ink-muted capitalize">{type.replace(/_/g, ' ')}</span>
                    <span className="font-mono text-signal-danger">{count}</span>
                  </div>
                ))
              ) : (
                <p className="text-ink-faint text-sm font-mono">No violations recorded</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
