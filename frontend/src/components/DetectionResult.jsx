import { useEffect, useRef } from 'react'
import './DetectionResult.css'

export default function DetectionResult({ result, previewUrl }) {
  const containerRef = useRef(null)
  const imgRef = useRef(null)
  const canvasRef = useRef(null)

  useEffect(() => {
    if (!result || !previewUrl) return

    const img = imgRef.current
    const canvas = canvasRef.current
    if (!img || !canvas) return

    const drawBoxes = () => {
      // Logic scaling: Rasio ukuran tampilan (display) dibanding ukuran asli (natural)
      const { width, height, naturalWidth, naturalHeight } = img
      
      // Samakan ukuran canvas dengan ukuran gambar yang tampil di layar
      canvas.width = width
      canvas.height = height
      
      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, width, height)
      
      const scaleX = width / naturalWidth
      const scaleY = height / naturalHeight

      result.detections.forEach((d) => {
        const [x1, y1, x2, y2] = d.bbox
        
        // Terapkan scaling ke koordinat
        const bx = x1 * scaleX
        const by = y1 * scaleY
        const bw = (x2 - x1) * scaleX
        const bh = (y2 - y1) * scaleY

        // Gaya Bounding Box
        ctx.strokeStyle = '#f97316'
        ctx.lineWidth = 2
        ctx.strokeRect(bx, by, bw, bh)

        // Gaya Label
        const label = `K${d.id} ${(d.confidence * 100).toFixed(0)}%`
        ctx.font = 'bold 11px Inter, sans-serif'
        const textWidth = ctx.measureText(label).width
        
        ctx.fillStyle = '#f97316'
        ctx.fillRect(bx, by > 20 ? by - 20 : by, textWidth + 8, 20)
        
        ctx.fillStyle = '#ffffff'
        ctx.fillText(label, bx + 4, by > 20 ? by - 6 : by + 14)
      })
    }

    // Jalankan saat gambar selesai dimuat
    if (img.complete) {
      drawBoxes()
    } else {
      img.onload = drawBoxes
    }

    // ResizeObserver: Menangani perubahan ukuran layar (responsivitas) secara realtime
    const ro = new ResizeObserver(() => drawBoxes())
    ro.observe(img)

    return () => ro.disconnect()
  }, [result, previewUrl])

  if (!result) return null

  return (
    <div className="detection-card" ref={containerRef}>
      <div className="result-info">
        <div className="res-header">
          <h4>{result.filename}</h4>
          <span className={`status-badge ${result.total_victims > 0 ? 'found' : 'clear'}`}>
            {result.total_victims > 0 ? `${result.total_victims} Victims` : 'Area Clear'}
          </span>
        </div>
      </div>

      <div className="canvas-wrapper">
        <img ref={imgRef} src={previewUrl} alt="Scan Result" className="base-image" />
        <canvas ref={canvasRef} className="box-overlay" />
      </div>

      <div className="result-table-wrapper">
        <table className="mini-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Conf</th>
              <th>Coordinates</th>
            </tr>
          </thead>
          <tbody>
            {result.detections.map(d => (
              <tr key={d.id}>
                <td><span className="id-tag">K{d.id}</span></td>
                <td>{(d.confidence * 100).toFixed(0)}%</td>
                <td><code>{d.lat?.toFixed(6)}, {d.lon?.toFixed(6)}</code></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
