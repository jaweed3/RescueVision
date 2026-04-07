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

      <style jsx>{`
        .status-container {
          display: flex;
          gap: 0.5rem;
          margin-top: 0.5rem;
          flex-wrap: wrap;
        }
        .status-chip-mini {
          display: flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.2rem 0.6rem;
          border-radius: 4px;
          font-size: 0.65rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.02em;
          border: 1px solid var(--border);
        }
        .dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
        }
        /* State Colors */
        .active {
          border-color: rgba(16, 185, 129, 0.4);
          background: rgba(16, 185, 129, 0.1);
          color: #10b981;
        }
        .active .dot { background: #10b981; box-shadow: 0 0 6px #10b981; }
        
        .inactive {
          border-color: rgba(239, 68, 68, 0.4);
          background: rgba(239, 68, 68, 0.1);
          color: #ef4444;
        }
        .inactive .dot { background: #ef4444; box-shadow: 0 0 6px #ef4444; }

        @media (max-width: 480px) {
          .status-container { gap: 0.25rem; }
          .status-chip-mini { padding: 0.15rem 0.4rem; font-size: 0.6rem; }
        }
      `}</style>
    </div>
  )
}
