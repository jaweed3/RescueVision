import { useRef, useState } from 'react'
import './UploadZone.css'

export default function UploadZone({ onUpload, loading }) {
  const inputRef = useRef()
  const [dragging, setDragging] = useState(false)

  const handleFiles = (fileList) => {
    const files = Array.from(fileList || [])
    if (!files.length) return

    const valid = ['image/jpeg', 'image/png', 'image/jpg']
    const invalid = files.filter((f) => !valid.includes(f.type))
    if (invalid.length > 0) {
      alert('Sebagian file tidak didukung. Gunakan hanya JPG atau PNG.')
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
        <p>Memproses...</p>
      ) : (
        <>
          <span>📷</span>
          <p>Drag & drop foto drone (multi-file)</p>
          <small>atau klik untuk pilih banyak file (JPG/PNG)</small>
          <small className="hint-dji">Foto DJI: GPS koordinat otomatis terbaca</small>
        </>
      )}
    </div>
  )
}
