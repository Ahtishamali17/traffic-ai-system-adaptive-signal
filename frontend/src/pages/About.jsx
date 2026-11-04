import TopBar from '../components/TopBar.jsx'

const STACK = [
  { layer: 'Detection', tech: 'YOLOv8 (Ultralytics)' },
  { layer: 'Tracking', tech: 'DeepSORT' },
  { layer: 'Backend', tech: 'FastAPI, OpenCV, PyTorch' },
  { layer: 'Frontend', tech: 'React, Vite, TailwindCSS, Chart.js' },
  { layer: 'Database', tech: 'MongoDB' },
  { layer: 'Deployment', tech: 'Docker, Nginx' },
]

export default function About() {
  return (
    <>
      <TopBar title="About" subtitle="System architecture and technology" />
      <div className="p-6 max-w-2xl space-y-6">
        <div className="glass-panel p-6">
          <h2 className="font-display font-semibold text-xl mb-3">Sentry Traffic Monitoring</h2>
          <p className="text-ink-muted text-sm leading-relaxed">
            An AI-powered vehicle detection and analytics platform. Sentry ingests footage from CCTV
            cameras, dashcams, drones, webcams, and uploaded video, detects and tracks every vehicle in
            frame, estimates speed, flags traffic violations, and surfaces it all through a live
            dashboard with exportable reports.
          </p>
        </div>

        <div className="glass-panel p-6">
          <span className="eyebrow">Technology Stack</span>
          <div className="mt-4 space-y-3">
            {STACK.map((row) => (
              <div key={row.layer} className="flex items-center justify-between text-sm border-b border-hairline/60 pb-3 last:border-0 last:pb-0">
                <span className="text-ink-muted">{row.layer}</span>
                <span className="font-mono">{row.tech}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel p-6">
          <span className="eyebrow">Pipeline</span>
          <ol className="mt-4 space-y-2 text-sm text-ink-muted list-decimal list-inside">
            <li>Video source (webcam / RTSP / file) streams frames into the detection engine</li>
            <li>YOLOv8 detects and classifies every vehicle in each frame</li>
            <li>DeepSORT assigns a permanent ID and maintains trajectory across frames</li>
            <li>Speed, direction, and violation rules evaluate each track in real time</li>
            <li>Events persist to MongoDB and trigger Telegram/email alerts when configured</li>
            <li>The dashboard streams the annotated feed and live stats over MJPEG + REST</li>
          </ol>
        </div>
      </div>
    </>
  )
}
