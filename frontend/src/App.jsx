import { useState, useRef } from 'react'
import axios from 'axios'
import DetectionResult from './components/DetectionResult'
import VictimMap from './components/VictimMap'
import UploadZone from './components/UploadZone'
import StatusBar from './components/StatusBar'
import './App.css'

const API = 'http://localhost:8000'

export default function App() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [manualGPS, setManualGPS] = useState({ lat: '', lon: '', alt: '80' })
  const [useManualGPS, setUseManualGPS] = useState(false)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [systemStatus, setSystemStatus] = useState(null)

  // Check system health on load
  useState(() => {
    axios.get(`${API}/health`)
      .then(r => setSystemStatus(r.data))
      .catch(() => setSystemStatus({ status: 'error', model_loaded: false }))
  }, [])

  const handleUpload = async (file) => {
    setLoading(true)
    setError(null)
    setResults(null)
    setPreviewUrl(URL.createObjectURL(file))

    const formData = new FormData()
    formData.append('file', file)

    // Append manual GPS if provided
    const params = new URLSearchParams()
    if (useManualGPS && manualGPS.lat && manualGPS.lon) {
      params.append('manual_lat', manualGPS.lat)
      params.append('manual_lon', manualGPS.lon)
      params.append('manual_altitude', manualGPS.alt || '80')
    }

    try {
      const res = await axios.post(
        `${API}/detect?${params.toString()}`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )
      setResults(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Detection failed. Check backend connection.')
    } finally {
      setLoading(false)
    }
  }

  const handleExport = () => {
    window.open(`${API}/export/csv`, '_blank')
  }

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

          {results && !loading && (
            <>
              {/* Stats */}
              <div className="stats-row">
                <div className="stat-card urgent">
                  <span className="stat-num">{results.total_victims}</span>
                  <span className="stat-label">Korban Terdeteksi</span>
                </div>
                <div className="stat-card">
                  <span className="stat-num">{results.inference_ms}ms</span>
                  <span className="stat-label">Waktu Inferensi</span>
                </div>
                <div className="stat-card">
                  <span className="stat-num">{results.gps_source.toUpperCase()}</span>
                  <span className="stat-label">Sumber GPS</span>
                </div>
              </div>

              {/* Detection visualization */}
              <DetectionResult
                result={results}
                previewUrl={previewUrl}
              />

              {/* Map */}
              {results.detections.some(d => d.lat) && (
                <VictimMap detections={results.detections} />
              )}

              {/* Export */}
              <button className="btn-export" onClick={handleExport}>
                📥 Export Koordinat CSV
              </button>
            </>
          )}

          {!results && !loading && !error && (
            <div className="empty-state">
              <span>🛸</span>
              <h3>Upload foto drone untuk memulai deteksi</h3>
              <p>Sistem mendukung foto DJI dengan GPS EXIF otomatis</p>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
