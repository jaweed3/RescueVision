import './StatusBar.css'

export default function StatusBar({ status }) {
  const backendUp = !!status && status.status === 'ok'
  const modelReady = !!status && status.model_loaded === true

  return (
    <div className="status-container">
      <div className={`status-chip-mini ${backendUp ? 'active' : 'inactive'}`}>
        <span className="dot"></span>
        {backendUp ? 'Backend: Online' : 'Backend: Offline'}
      </div>
      <div className={`status-chip-mini ${modelReady ? 'active' : 'inactive'}`}>
        <span className="dot"></span>
        {modelReady ? 'Model: Ready' : 'Model: Missing'}
      </div>
    </div>
  )
}
