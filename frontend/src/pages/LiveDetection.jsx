import { useEffect, useState } from 'react'
import { LuPlay, LuSquare, LuUpload, LuPlus, LuTrash2 } from 'react-icons/lu'
import TopBar from '../components/TopBar.jsx'
import StatCard from '../components/StatCard.jsx'
import SignalPanel from '../components/SignalPanel.jsx'
import { detectionApi } from '../api/client.js'

const SOURCE_TYPES = [
  { value: 'webcam', label: 'Webcam' },
  { value: 'rtsp', label: 'RTSP Stream' },
  { value: 'ip_camera', label: 'IP Camera' },
  { value: 'uploaded_file', label: 'Uploaded Video' },
]

let laneIdCounter = 0
function newLane(name) {
  laneIdCounter += 1
  return { id: laneIdCounter, name, x: 0, y: 0, width: 200, height: 200 }
}

export default function LiveDetection() {
  const [sourceType, setSourceType] = useState('webcam')
  const [source, setSource] = useState('0')
  const [cameraId, setCameraId] = useState('gate-1')
  const [frameSkip, setFrameSkip] = useState(3)
  const [uploading, setUploading] = useState(false)
  const [activeSession, setActiveSession] = useState(null)
  const [sessionInfo, setSessionInfo] = useState(null)
  const [error, setError] = useState(null)

  // --- Adaptive signal (optional) ---
  const [adaptiveEnabled, setAdaptiveEnabled] = useState(false)
  const [lanes, setLanes] = useState([newLane('north'), newLane('south')])
  const [minGreen, setMinGreen] = useState(10)
  const [maxGreen, setMaxGreen] = useState(60)
  const [signalStatus, setSignalStatus] = useState(null)

  useEffect(() => {
    if (!activeSession) return
    const interval = setInterval(async () => {
      try {
        const res = await detectionApi.getSession(activeSession)
        setSessionInfo(res.data)
        if (res.data.status === 'error' || res.data.status === 'stopped') {
          clearInterval(interval)
        }
      } catch {
        /* session may have been removed server-side; ignore transient errors */
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [activeSession])

  useEffect(() => {
    if (!activeSession || !adaptiveEnabled) return
    const interval = setInterval(async () => {
      try {
        const res = await detectionApi.getSignals(activeSession)
        setSignalStatus(res.data)
      } catch {
        /* 409 until adaptive signal actually engages, or session ended; ignore */
      }
    }, 1500)
    return () => clearInterval(interval)
  }, [activeSession, adaptiveEnabled])

  function updateLane(id, field, value) {
    setLanes((prev) => prev.map((l) => (l.id === id ? { ...l, [field]: value } : l)))
  }

  function addLane() {
    setLanes((prev) => [...prev, newLane(`lane-${prev.length + 1}`)])
  }

  function removeLane(id) {
    setLanes((prev) => (prev.length > 2 ? prev.filter((l) => l.id !== id) : prev))
  }

  function laneToPolygon(lane) {
    const x = Number(lane.x), y = Number(lane.y), w = Number(lane.width), h = Number(lane.height)
    return {
      name: lane.name,
      polygon: [
        { x, y }, { x: x + w, y }, { x: x + w, y: y + h }, { x, y: y + h },
      ],
    }
  }

  async function handleUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      const res = await detectionApi.uploadVideo(file)
      setSource(res.data.server_path)
      setSourceType('uploaded_file')
    } catch (err) {
      setError('Upload failed. Check the file type (mp4/avi/mov/mkv/webm) and size (max 500MB).')
    } finally {
      setUploading(false)
    }
  }

  async function handleStart() {
    setError(null)
    setSignalStatus(null)
    try {
      const payload = {
        source_type: sourceType,
        source,
        camera_id: cameraId,
        confidence_threshold: 0.4,
        frame_skip: Math.min(10, Math.max(1, Number(frameSkip) || 1)),
        enable_tracking: true,
      }

      if (adaptiveEnabled) {
        if (lanes.length < 2) {
          setError('Adaptive signal needs at least 2 lanes.')
          return
        }
        payload.adaptive_signal = {
          enabled: true,
          lanes: lanes.map(laneToPolygon),
          min_green_seconds: Number(minGreen),
          max_green_seconds: Number(maxGreen),
        }
      }

      const res = await detectionApi.start(payload)
      setActiveSession(res.data.session_id)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start detection session.')
    }
  }

  async function handleStop() {
    if (!activeSession) return
    try {
      await detectionApi.stop(activeSession)
    } finally {
      setActiveSession(null)
      setSessionInfo(null)
      setSignalStatus(null)
    }
  }

  return (
    <>
      <TopBar title="Live Detection" subtitle="Start a session against a webcam, stream, or uploaded video" />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* --- Controls --- */}
        <div className="glass-panel p-5 space-y-4 h-fit">
          <span className="eyebrow">Session Setup</span>

          <div>
            <label className="text-xs text-ink-muted block mb-1.5">Camera ID</label>
            <input
              value={cameraId}
              onChange={(e) => setCameraId(e.target.value)}
              disabled={!!activeSession}
              className="w-full bg-panel-raised border border-hairline rounded-lg px-3 py-2 text-sm font-mono disabled:opacity-50"
            />
          </div>

          <div>
            <label className="text-xs text-ink-muted block mb-1.5">Source Type</label>
            <select
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
              disabled={!!activeSession}
              className="w-full bg-panel-raised border border-hairline rounded-lg px-3 py-2 text-sm disabled:opacity-50"
            >
              {SOURCE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          {sourceType === 'uploaded_file' ? (
            <div>
              <label className="text-xs text-ink-muted block mb-1.5">Video File</label>
              <label className="flex items-center justify-center gap-2 w-full border border-dashed border-hairline rounded-lg px-3 py-4 text-sm text-ink-muted cursor-pointer hover:border-signal-amber/40 transition-colors">
                <LuUpload size={16} />
                {uploading ? 'Uploading…' : source.includes('/') ? 'File ready' : 'Choose video file'}
                <input type="file" accept=".mp4,.avi,.mov,.mkv,.webm" className="hidden" onChange={handleUpload} />
              </label>
            </div>
          ) : (
            <div>
              <label className="text-xs text-ink-muted block mb-1.5">
                {sourceType === 'webcam' ? 'Device Index' : 'Stream URL'}
              </label>
              <input
                value={source}
                onChange={(e) => setSource(e.target.value)}
                disabled={!!activeSession}
                placeholder={sourceType === 'webcam' ? '0' : 'rtsp://user:pass@host/stream'}
                className="w-full bg-panel-raised border border-hairline rounded-lg px-3 py-2 text-sm font-mono disabled:opacity-50"
              />
            </div>
          )}

          <div>
            <label className="text-xs text-ink-muted block mb-1.5">
              Frame Skip: process every {frameSkip}{Number(frameSkip) === 1 ? 'st' : Number(frameSkip) === 2 ? 'nd' : Number(frameSkip) === 3 ? 'rd' : 'th'} frame
            </label>
            <input
              type="range" min={1} max={10} value={frameSkip}
              onChange={(e) => setFrameSkip(e.target.value)}
              disabled={!!activeSession}
              className="w-full accent-signal-amber disabled:opacity-50"
            />
            <p className="text-ink-faint text-xs mt-1">
              Video slow ho to badhao (3-5). 1 = har frame (sabse accurate, sabse slow).
            </p>
          </div>

          {/* --- Adaptive Signal Config --- */}
          <div className="border-t border-hairline pt-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={adaptiveEnabled}
                onChange={(e) => setAdaptiveEnabled(e.target.checked)}
                disabled={!!activeSession}
                className="accent-signal-amber"
              />
              <span className="text-sm font-medium">Adaptive Signal Control</span>
            </label>
            <p className="text-ink-faint text-xs mt-1">
              Green-light time adapts to each lane's live vehicle density instead of a fixed timer.
            </p>

            {adaptiveEnabled && (
              <div className="mt-3 space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-ink-muted block mb-1">Min Green (s)</label>
                    <input
                      type="number" min={1} value={minGreen}
                      onChange={(e) => setMinGreen(e.target.value)}
                      disabled={!!activeSession}
                      className="w-full bg-panel-raised border border-hairline rounded-lg px-2 py-1.5 text-sm font-mono disabled:opacity-50"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-ink-muted block mb-1">Max Green (s)</label>
                    <input
                      type="number" min={1} value={maxGreen}
                      onChange={(e) => setMaxGreen(e.target.value)}
                      disabled={!!activeSession}
                      className="w-full bg-panel-raised border border-hairline rounded-lg px-2 py-1.5 text-sm font-mono disabled:opacity-50"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <p className="text-xs text-ink-muted">
                    Lanes (rectangle zones in frame pixels — x/y = top-left corner)
                  </p>
                  {lanes.map((lane) => (
                    <div key={lane.id} className="bg-panel-raised border border-hairline rounded-lg p-2.5 space-y-1.5">
                      <div className="flex items-center gap-2">
                        <input
                          value={lane.name}
                          onChange={(e) => updateLane(lane.id, 'name', e.target.value)}
                          disabled={!!activeSession}
                          placeholder="lane name"
                          className="flex-1 bg-void border border-hairline rounded px-2 py-1 text-xs font-mono disabled:opacity-50"
                        />
                        {lanes.length > 2 && !activeSession && (
                          <button onClick={() => removeLane(lane.id)} className="text-ink-faint hover:text-signal-danger">
                            <LuTrash2 size={14} />
                          </button>
                        )}
                      </div>
                      <div className="grid grid-cols-4 gap-1.5">
                        {['x', 'y', 'width', 'height'].map((field) => (
                          <input
                            key={field}
                            type="number"
                            value={lane[field]}
                            onChange={(e) => updateLane(lane.id, field, e.target.value)}
                            disabled={!!activeSession}
                            placeholder={field}
                            className="bg-void border border-hairline rounded px-1.5 py-1 text-[11px] font-mono disabled:opacity-50"
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                  {!activeSession && (
                    <button
                      onClick={addLane}
                      className="w-full flex items-center justify-center gap-1.5 text-xs text-signal-amber border border-dashed border-signal-amber/30 rounded-lg py-1.5 hover:bg-signal-amber/5"
                    >
                      <LuPlus size={13} /> Add Lane
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>

          {error && <p className="text-signal-danger text-xs">{error}</p>}

          {!activeSession ? (
            <button onClick={handleStart} className="btn-primary w-full flex items-center justify-center gap-2">
              <LuPlay size={16} /> Start Detection
            </button>
          ) : (
            <button
              onClick={handleStop}
              className="w-full flex items-center justify-center gap-2 bg-signal-danger/10 border border-signal-danger/30 text-signal-danger font-display font-semibold px-4 py-2 rounded-lg hover:bg-signal-danger/20 transition-colors"
            >
              <LuSquare size={16} /> Stop Detection
            </button>
          )}
        </div>

        {/* --- Live Feed --- */}
        <div className="lg:col-span-2 space-y-4">
          <div className="glass-panel aspect-video flex items-center justify-center overflow-hidden">
            {activeSession && sessionInfo?.status === 'running' ? (
              <img
                src={detectionApi.streamUrl(activeSession)}
                alt="Live detection feed"
                className="w-full h-full object-contain"
              />
            ) : (
              <p className="text-ink-faint text-sm font-mono">
                {activeSession ? `Session ${sessionInfo?.status ?? 'starting…'}` : 'No active stream'}
              </p>
            )}
          </div>

          {sessionInfo && (
            <div className="grid grid-cols-3 gap-4">
              <StatCard label="FPS" value={sessionInfo.current_fps} accent="safe" />
              <StatCard label="Frames" value={sessionInfo.total_frames_processed} accent="default" />
              <StatCard label="Status" value={sessionInfo.status.toUpperCase()} accent="amber" />
            </div>
          )}

          {adaptiveEnabled && signalStatus && <SignalPanel status={signalStatus} />}
        </div>
      </div>
    </>
  )
}

