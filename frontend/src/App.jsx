import { useEffect, useState } from 'react'
import axios from 'axios'
import DetectionResult from './components/DetectionResult'
import VictimMap from './components/VictimMap'
import UploadZone from './components/UploadZone'
import StatusBar from './components/StatusBar'
import './App.css'

const API = ''

export default function App() {
  const [singleResult, setSingleResult] = useState(null)
  const [batchResult, setBatchResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [manualGPS, setManualGPS] = useState({ lat: '', lon: '', alt: '80' })
  const [useManualGPS, setUseManualGPS] = useState(false)
  const [previewUrls, setPreviewUrls] = useState([])
  const [systemStatus, setSystemStatus] = useState(null)

  // Check system health on load
  useEffect(() => {
    axios.get(`${API}/health`)
      .then(r => setSystemStatus(r.data))
      .catch(() => setSystemStatus({ status: 'error', model_loaded: false }))
  }, [])

  const handleUpload = async (files) => {
    if (!files?.length) return

    setLoading(true)
    setError(null)
    setSingleResult(null)
    setBatchResult(null)

    // Release previous object URLs to avoid memory leaks on repeated uploads.
    setPreviewUrls((prev) => {
      prev.forEach((u) => URL.revokeObjectURL(u))
      return files.map((f) => URL.createObjectURL(f))
    })

    // Append manual GPS if provided
    const params = new URLSearchParams()
    if (useManualGPS && manualGPS.lat && manualGPS.lon) {
      params.append('manual_lat', manualGPS.lat)
      params.append('manual_lon', manualGPS.lon)
      params.append('manual_altitude', manualGPS.alt || '80')
    }

    try {
      if (files.length === 1) {
        const formData = new FormData()
        formData.append('file', files[0])

        const res = await axios.post(
          `${API}/detect?${params.toString()}`,
          formData,
          { headers: { 'Content-Type': 'multipart/form-data' } }
        )
        setSingleResult(res.data)
      } else {
        const formData = new FormData()
        files.forEach((f) => formData.append('files', f))

        const res = await axios.post(
          `${API}/detect/batch?${params.toString()}`,
          formData,
          { headers: { 'Content-Type': 'multipart/form-data' } }
        )
        setBatchResult(res.data)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Detection failed. Check backend connection.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    return () => {
      previewUrls.forEach((u) => URL.revokeObjectURL(u))
    }
  }, [previewUrls])

  const handleExport = () => {
    window.open(`${API}/export/csv`, '_blank')
  }

  const hasSingle = !!singleResult
  const hasBatch = !!batchResult
  const hasResults = hasSingle || hasBatch

  const mergedDetections = hasBatch
    ? batchResult.results.flatMap((r, i) =>
        r.detections.map((d, j) => ({ ...d, id: i * 1000 + j + 1 }))
      )
    : hasSingle
      ? singleResult.detections
      : []

  const avgInferenceMs = hasBatch && batchResult.total_images > 0
    ? (
      batchResult.results.reduce((sum, r) => sum + (r.inference_ms || 0), 0) /
      batchResult.total_images
    ).toFixed(1)
    : hasSingle
      ? singleResult.inference_ms
      : null

  const gpsLabel = hasBatch
    ? 'MIXED'
    : hasSingle
      ? singleResult.gps_source.toUpperCase()
      : '-'

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <span className="logo-icon">🛸</span>
            <div>
              <h1>RescueVision Edge</h1>
              <p>Sistem Deteksi Korban Bencana — On-Device AI</p>
            </div>
          </div>
          <StatusBar status={systemStatus} />
        </div>
      </header>

      <main className="main">
        {/* Left Panel — Upload & Config */}
        <aside className="sidebar">
          <section className="card">
            <h2>📤 Upload Foto Drone</h2>
            <UploadZone onUpload={handleUpload} loading={loading} />
            <p className="hint batch-hint">Bisa pilih banyak foto sekaligus untuk deteksi batch.</p>
          </section>

          {/* GPS Configuration */}
          <section className="card">
            <h2>📍 Koordinat GPS</h2>
            <label className="toggle">
              <input
                type="checkbox"
                checked={useManualGPS}
                onChange={e => setUseManualGPS(e.target.checked)}
              />
              <span>Input koordinat manual</span>
            </label>
            <p className="hint">
              {useManualGPS
                ? 'Masukkan koordinat area survei secara manual'
                : 'Sistem akan membaca GPS dari EXIF foto DJI otomatis'}
            </p>

            {useManualGPS && (
              <div className="gps-inputs">
                <label>
                  Latitude
                  <input
                    type="number"
                    step="0.000001"
                    placeholder="-7.342100"
                    value={manualGPS.lat}
                    onChange={e => setManualGPS(p => ({ ...p, lat: e.target.value }))}
                  />
                </label>
                <label>
                  Longitude
                  <input
                    type="number"
                    step="0.000001"
                    placeholder="110.452300"
                    value={manualGPS.lon}
                    onChange={e => setManualGPS(p => ({ ...p, lon: e.target.value }))}
                  />
                </label>
                <label>
                  Ketinggian (m)
                  <input
                    type="number"
                    placeholder="80"
                    value={manualGPS.alt}
                    onChange={e => setManualGPS(p => ({ ...p, alt: e.target.value }))}
                  />
                </label>
              </div>
            )}
          </section>
        </aside>

        {/* Center — Results */}
        <section className="content">
          {error && (
            <div className="error-banner">
              ⚠️ {error}
            </div>
          )}

          {loading && (
            <div className="loading-state">
              <div className="spinner" />
              <p>Menjalankan deteksi AI...</p>
              <small>Model YOLOv8n — CPU inference</small>
            </div>
          )}

          {hasResults && !loading && (
            <>
              {/* Stats */}
              <div className="stats-row">
                <div className="stat-card urgent">
                  <span className="stat-num">{hasBatch ? batchResult.total_victims : singleResult.total_victims}</span>
                  <span className="stat-label">Korban Terdeteksi</span>
                </div>
                <div className="stat-card">
                  <span className="stat-num">{avgInferenceMs}ms</span>
                  <span className="stat-label">Rata-rata Inferensi</span>
                </div>
                <div className="stat-card">
                  <span className="stat-num">{hasBatch ? batchResult.total_images : 1}</span>
                  <span className="stat-label">Total Gambar</span>
                </div>
                <div className="stat-card">
                  <span className="stat-num">{gpsLabel}</span>
                  <span className="stat-label">Sumber GPS</span>
                </div>
              </div>

              {/* Detection visualization */}
              {hasSingle && (
                <DetectionResult
                  result={singleResult}
                  previewUrl={previewUrls[0]}
                />
              )}

              {hasBatch && (
                <div className="batch-results">
                  {batchResult.results.map((item, idx) => (
                    <DetectionResult
                      key={`${item.filename}-${idx}`}
                      result={item}
                      previewUrl={previewUrls[idx]}
                    />
                  ))}
                </div>
              )}

              {/* Map */}
              {mergedDetections.some(d => d.lat) && (
                <VictimMap detections={mergedDetections} />
              )}

              {/* Export */}
              <button className="btn-export" onClick={handleExport}>
                📥 Export Koordinat CSV
              </button>
            </>
          )}

          {!hasResults && !loading && !error && (
            <div className="empty-state">
              <span>🛸</span>
              <h3>Upload satu atau banyak foto drone untuk memulai deteksi</h3>
              <p>Sistem mendukung batch processing dan GPS EXIF otomatis</p>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
