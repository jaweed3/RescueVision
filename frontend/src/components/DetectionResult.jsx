import './DetectionResult.css'

export default function DetectionResult({ result, previewUrl }) {
  if (!result) return null

  return (
    <div className="detection-result">
      {/* Image preview with bbox overlay — simplified text table for now */}
      {/* In Tahap 3, add canvas overlay for bounding boxes */}

      <div className="result-header">
        <h3>Hasil Deteksi: {result.filename}</h3>
        <span className={`badge ${result.total_victims > 0 ? 'alert' : 'clear'}`}>
          {result.total_victims > 0 ? `⚠️ ${result.total_victims} Korban` : '✅ Area Aman'}
        </span>
      </div>

      {previewUrl && (
        <div className="preview-container">
          <img src={previewUrl} alt="Drone foto" className="preview-img" />
        </div>
      )}

      {result.detections.length > 0 && (
        <table className="victim-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Confidence</th>
              <th>Latitude</th>
              <th>Longitude</th>
              <th>Akurasi</th>
              <th>Posisi Relatif</th>
            </tr>
          </thead>
          <tbody>
            {result.detections.map(d => (
              <tr key={d.id}>
                <td><span className="victim-id">K{d.id}</span></td>
                <td>
                  <span className={`conf ${d.confidence > 0.7 ? 'high' : d.confidence > 0.5 ? 'med' : 'low'}`}>
                    {(d.confidence * 100).toFixed(1)}%
                  </span>
                </td>
                <td>{d.lat ? d.lat.toFixed(6) : '—'}</td>
                <td>{d.lon ? d.lon.toFixed(6) : '—'}</td>
                <td>{d.accuracy_m ? `±${d.accuracy_m}m` : '—'}</td>
                <td>
                  {`X:${(d.cx_rel * 100).toFixed(0)}% Y:${(d.cy_rel * 100).toFixed(0)}%`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="result-meta">
        <span>🕐 Inferensi: {result.inference_ms}ms</span>
        <span>📡 GPS: {result.gps_source === 'exif' ? 'EXIF DJI' : result.gps_source === 'manual' ? 'Manual' : 'Tidak tersedia'}</span>
        {result.ref_coords.lat && (
          <span>📍 Ref: {result.ref_coords.lat?.toFixed(4)}, {result.ref_coords.lon?.toFixed(4)}</span>
        )}
      </div>
    </div>
  )
}
