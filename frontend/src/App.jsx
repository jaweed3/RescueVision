import DetectionResult from './components/DetectionResult'
import VictimMap from './components/VictimMap'
import UploadZone from './components/UploadZone'
import StatusBar from './components/StatusBar'
import { useAppLogic } from './hooks/useAppLogic'
import './App.css'

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

/**
 * Main RescueVision Application Component
 * Focuses purely on UI layout and presentation.
 */
export default function App() {
  const { state, actions } = useAppLogic()
  
  const { 
    loading, error, manualGPS, useManualGPS, geolocating, 
    geoError, previewUrls, systemStatus, results, allDetections, stats 
  } = state

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
        <aside className="app-sidebar">
          <div className="sidebar-card">
            <div className="card-header-main">
              <div className="card-header-title">
                <Icons.Upload />
                <h3>Data Input</h3>
              </div>
              <StatusBar status={systemStatus} />
            </div>
            <UploadZone onUpload={actions.handleUpload} loading={loading} />
          </div>

          <div className="sidebar-card">
            <div className="card-header">
              <Icons.GPS />
              <h3>Mission Parameters</h3>
            </div>
            <div className="gps-config">
              <label className="checkbox-field">
                <input type="checkbox" checked={useManualGPS} onChange={e => actions.setUseManualGPS(e.target.checked)} />
                <span>Override GPS Exif</span>
              </label>

              <button className="btn-device-gps" onClick={actions.handleDeviceGPS} disabled={geolocating}>
                <Icons.GPS />
                {geolocating ? 'Fetching GPS...' : 'Use Device GPS'}
              </button>

              {geoError && <p className="field-hint field-hint--error">{geoError}</p>}

              {useManualGPS && (
                <div className="gps-grid">
                  <div className="field">
                    <label>Latitude</label>
                    <input type="number" step="0.000001" value={manualGPS.lat} onChange={e => actions.setManualGPS(p => ({ ...p, lat: e.target.value }))} />
                  </div>
                  <div className="field">
                    <label>Longitude</label>
                    <input type="number" step="0.000001" value={manualGPS.lon} onChange={e => actions.setManualGPS(p => ({ ...p, lon: e.target.value }))} />
                  </div>
                  <div className="field full">
                    <label>Altitude (m AGL)</label>
                    <input type="number" value={manualGPS.alt} onChange={e => actions.setManualGPS(p => ({ ...p, alt: e.target.value }))} />
                  </div>
                </div>
              )}
            </div>
          </div>

          {allDetections.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <button className="btn-primary" onClick={actions.handleExport}><Icons.Export /> Export CSV</button>
              <button className="btn-device-gps" style={{ opacity: 0.6 }} onClick={actions.handleClear}>Clear Session</button>
            </div>
          )}
        </aside>

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
              <h2>Ready for Mission</h2>
              <p>Upload drone imagery or video clips to begin victim localization.</p>
            </div>
          )}

          {results.length > 0 && !loading && (
            <div className="results-wrapper">
              <div className="analytics-grid">
                <div className={`analytic-item ${stats.victims > 0 ? 'critical' : ''}`}>
                  <label>Victims</label>
                  <div className="value">{stats.victims}</div>
                </div>
                <div className="analytic-item">
                  <label>Avg Inference</label>
                  <div className="value">{stats.inference}<span>ms</span></div>
                </div>
                <div className="analytic-item">
                  <label>Images</label>
                  <div className="value">{stats.images}</div>
                </div>
                <div className="analytic-item">
                  <label>GPS Status</label>
                  <div className="value small">{stats.gps}</div>
                </div>
              </div>

              <div className="visualization-grid">
                {results.map((item, idx) => (
                  <DetectionResult key={`${item.filename}-${idx}`} result={item} previewUrl={previewUrls[idx]} />
                ))}
              </div>

              {allDetections.some(d => d.lat) && (
                <div className="main-card map-section-wide">
                  <div className="card-header"><Icons.GPS /> <h3>Mission Map</h3></div>
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
