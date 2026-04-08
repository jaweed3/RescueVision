import { useEffect, useState, useRef } from 'react'
import axios from 'axios'
import DetectionResult from './components/DetectionResult'
import VictimMap from './components/VictimMap'
import UploadZone from './components/UploadZone'
import StatusBar from './components/StatusBar'
import './App.css'

const API = import.meta.env.PROD ? '/api' : 'http://localhost:8000'

const Icons = {
  Logo: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>
    </svg>
  ),
  Upload: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
    </svg>
  ),
  GPS: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
    </svg>
  ),
  Empty: () => (
    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.2 }}>
      <path d="M2 20h20"/><path d="m7 3 5 5 5-5"/><path d="M12 8v12"/>
    </svg>
  ),
  Export: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
    </svg>
  )
}

export default function App() {
  const [singleResult, setSingleResult] = useState(null)
  const [batchResult, setBatchResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [manualGPS, setManualGPS] = useState({ lat: '', lon: '', alt: '80' })
  const [useManualGPS, setUseManualGPS] = useState(false)
  const [geolocating, setGeolocating] = useState(false)
  const [geoError, setGeoError] = useState(null)
  const [previewUrls, setPreviewUrls] = useState([])
  const [systemStatus, setSystemStatus] = useState(null)

  useEffect(() => {
    const checkHealth = () => {
      axios.get(`${API}/health`)
        .then(r => setSystemStatus(r.data))
        .catch(() => setSystemStatus({ status: 'error', model_loaded: false }))
    }
    checkHealth()
    const interval = setInterval(checkHealth, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleUpload = async (files) => {
    if (!files?.length) return
    setLoading(true)
    setError(null)
    previewUrls.forEach(URL.revokeObjectURL)
    const newUrls = files.map(f => URL.createObjectURL(f))
    setPreviewUrls(newUrls)

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
        const res = await axios.post(`${API}/detect?${params.toString()}`, formData)
        setSingleResult(res.data)
        setBatchResult(null)
      } else {
        const formData = new FormData()
        files.forEach(f => formData.append('files', f))
        const res = await axios.post(`${API}/detect/batch?${params.toString()}`, formData)
        setBatchResult(res.data)
        setSingleResult(null)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Gagal deteksi. Pastikan backend aktif.')
    } finally {
      setLoading(false)
    }
  }

  const handleDeviceGPS = () => {
    if (!navigator.geolocation) {
      setGeoError('Geolocation tidak didukung browser ini.')
      return
    }
    setGeolocating(true)
    setGeoError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude, altitude } = pos.coords
        setManualGPS({
          lat: latitude.toFixed(6),
          lon: longitude.toFixed(6),
          alt: altitude ? altitude.toFixed(1) : '80'
        })
        setUseManualGPS(true)
        setGeolocating(false)
      },
      (err) => {
        setGeoError(`GPS gagal: ${err.message}`)
        setGeolocating(false)
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    )
  }

  const handleExport = () => window.open(`${API}/export/csv`, '_blank')
  const handleClear = async () => {
    if (window.confirm('Hapus semua log deteksi di server?')) {
      await axios.post(`${API}/export/clear`)
      setSingleResult(null)
      setBatchResult(null)
    }
  }

  const results = batchResult ? batchResult.results : (singleResult ? [singleResult] : [])
  const allDetections = results.flatMap((r) => r.detections)

  const stats = {
    victims: batchResult ? batchResult.total_victims : (singleResult?.total_victims || 0),
    images: batchResult ? batchResult.total_images : (singleResult ? 1 : 0),
    inference: batchResult 
      ? (batchResult.results.reduce((s, r) => s + r.inference_ms, 0) / batchResult.total_images).toFixed(1)
      : singleResult?.inference_ms || 0,
    gps: singleResult ? singleResult.gps_source.toUpperCase() : (batchResult ? 'MIXED' : '-')
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-inner">
          <div className="brand">
            <div className="brand-logo"><Icons.Logo /></div>
            <div className="brand-text">
              <h1>RescueVision <span>Edge</span></h1>
              <p>Search & Rescue AI — Offline Mode</p>
            </div>
          </div>
        </div>
      </header>

      <main className="app-main">
        {/* SIDEBAR (Left on PC) */}
        <aside className="app-sidebar">
          <div className="sidebar-card">
            <div className="card-header-main">
              <div className="card-header-title">
                <Icons.Upload />
                <h3>Data Input</h3>
              </div>
              <StatusBar status={systemStatus} />
            </div>
            <UploadZone onUpload={handleUpload} loading={loading} />
          </div>

          <div className="sidebar-card">
            <div className="card-header">
              <Icons.GPS />
              <h3>Mission Parameters</h3>
            </div>
            <div className="gps-config">
              <label className="checkbox-field">
                <input type="checkbox" checked={useManualGPS} onChange={e => setUseManualGPS(e.target.checked)} />
                <span>Override GPS Exif</span>
              </label>

              <button
                className="btn-device-gps"
                onClick={handleDeviceGPS}
                disabled={geolocating}
                title="Gunakan GPS perangkat ini sebagai koordinat referensi"
              >
                <Icons.GPS />
                {geolocating ? 'Mengambil lokasi...' : 'Use Device GPS'}
              </button>

              {geoError && <p className="field-hint field-hint--error">{geoError}</p>}

              {useManualGPS && (
                <div className="gps-grid">
                  <div className="field">
                    <label>Latitude</label>
                    <input type="number" step="0.000001" placeholder="-7.342..." value={manualGPS.lat} onChange={e => setManualGPS(p => ({ ...p, lat: e.target.value }))} />
                  </div>
                  <div className="field">
                    <label>Longitude</label>
                    <input type="number" step="0.000001" placeholder="110.45..." value={manualGPS.lon} onChange={e => setManualGPS(p => ({ ...p, lon: e.target.value }))} />
                  </div>
                  <div className="field full">
                    <label>Altitude terbang (m AGL)</label>
                    <input type="number" placeholder="80" value={manualGPS.alt} onChange={e => setManualGPS(p => ({ ...p, alt: e.target.value }))} />
                  </div>
                </div>
              )}
              {!useManualGPS && !manualGPS.lat && <p className="field-hint">Reading coordinates from DJI EXIF metadata automatically.</p>}
              {useManualGPS && manualGPS.lat && (
                <p className="field-hint">
                  Koordinat: {parseFloat(manualGPS.lat).toFixed(5)}, {parseFloat(manualGPS.lon).toFixed(5)} | Alt: {manualGPS.alt}m
                </p>
              )}
            </div>
          </div>

          {allDetections.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <button className="btn-primary" onClick={handleExport}>
                <Icons.Export /> Export CSV Report
              </button>
              <button className="btn-device-gps" style={{ borderColor: 'var(--border)', color: 'var(--text-dim)' }} onClick={handleClear}>
                Clear Session
              </button>
            </div>
          )}
        </aside>

        {/* CONTENT AREA (Main Visualization) */}
        <section className="app-content">
          {error && <div className="alert-error"><strong>System Error:</strong> {error}</div>}

          {loading && (
            <div className="loading-overlay">
              <div className="loader"></div>
              <p>Analyzing Drone Imagery...</p>
            </div>
          )}

          {!results.length && !loading && (
            <div className="empty-placeholder">
              <Icons.Empty />
              <h2>No Mission Data</h2>
              <p>Please upload drone imagery to begin victim localization.</p>
            </div>
          )}

          {results.length > 0 && !loading && (
            <div className="results-wrapper">
              <div className="analytics-grid">
                <div className={`analytic-item ${stats.victims > 0 ? 'critical' : ''}`}>
                  <label>Victims Detected</label>
                  <div className="value">{stats.victims}</div>
                </div>
                <div className="analytic-item">
                  <label>Mean Inference</label>
                  <div className="value">{stats.inference}<span>ms</span></div>
                </div>
                <div className="analytic-item">
                  <label>Processed</label>
                  <div className="value">{stats.images}<span>img</span></div>
                </div>
                <div className="analytic-item">
                  <label>GPS Lock</label>
                  <div className="value small">{stats.gps}</div>
                </div>
              </div>

              {/* Grid foto yang diunggah */}
              <div className="visualization-grid">
                {results.map((item, idx) => (
                  <DetectionResult key={`${item.filename}-${idx}`} result={item} previewUrl={previewUrls[idx]} />
                ))}
              </div>

              {/* Peta diletakkan di bawah foto (Full Width) */}
              {allDetections.some(d => d.lat) && (
                <div className="main-card map-section-wide">
                  <div className="card-header"><Icons.GPS /> <h3>Geospatial Context (Victim Map)</h3></div>
                  <VictimMap detections={allDetections} />
                </div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
