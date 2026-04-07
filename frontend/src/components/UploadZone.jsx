import { useRef, useState } from 'react'
import './UploadZone.css'

const UploadIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="upload-svg">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
  </svg>
)

export default function UploadZone({ onUpload, loading }) {
  const inputRef = useRef()
  const [dragging, setDragging] = useState(false)

  const handleFiles = (fileList) => {
    const files = Array.from(fileList || [])
    if (!files.length) return

    const valid = ['image/jpeg', 'image/png', 'image/jpg']
    const invalid = files.filter((f) => !valid.includes(f.type))
    if (invalid.length > 0) {
      alert('Format file tidak didukung. Gunakan JPG atau PNG.')
      return
    }

    onUpload(files)
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  return (
    <div
      className={`upload-zone ${dragging ? 'drag' : ''} ${loading ? 'loading' : ''}`}
      onClick={() => !loading && inputRef.current.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/jpeg,image/jpg,image/png"
        style={{ display: 'none' }}
        onChange={e => handleFiles(e.target.files)}
      />
      {loading ? (
        <div className="upload-loading">
          <div className="mini-spinner" />
          <p>Memproses file...</p>
        </div>
      ) : (
        <>
          <div className="icon-circle">
            <UploadIcon />
          </div>
          <div className="text-content">
            <p className="main-text">Drag & drop foto drone</p>
            <p className="sub-text">atau klik untuk pilih banyak file (JPG/PNG)</p>
          </div>
          <div className="dji-hint">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '12px' }}>
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <span>Auto-detect GPS (DJI Exif)</span>
          </div>
        </>
      )}
    </div>
  )
}
