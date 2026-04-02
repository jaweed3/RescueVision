export default function StatusBar({ status }) {
	const backendUp = !!status && status.status === 'ok'
	const modelReady = !!status && status.model_loaded === true

	return (
		<div className="status-bar">
			<span className={`status-chip ${backendUp ? 'ok' : 'err'}`}>
				{backendUp ? 'Backend Online' : 'Backend Offline'}
			</span>
			<span className={`status-chip ${modelReady ? 'ok' : 'warn'}`}>
				{modelReady ? 'Model Ready' : 'Model Missing'}
			</span>
		</div>
	)
}
