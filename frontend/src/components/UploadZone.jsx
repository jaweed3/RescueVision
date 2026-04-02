import { useRef, useState } from 'react'
import './UploadZone.css'

export default function UploadZone({ onUpload, loading }) {
  const inputRef = useRef()
  const [dragging, setDragging] = useState(false)

  const handleFile = (file) => {
    if (!file) return
    const valid = ['image/jpeg', 'image/png', 'image/jpg']
    if (!valid.includes(file.type)) {
      alert('Format tidak didukung. Gunakan JPG atau PNG.')
      return
    }
    onUpload(file)
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
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
        accept="image/jpeg,image/jpg,image/png"
        style={{ display: 'none' }}
        onChange={e => handleFile(e.target.files[0])}
      />
      {loading ? (
        <p>Memproses...</p>
      ) : (
        <>
          <span>📷</span>
          <p>Drag & drop foto drone</p>
          <small>atau klik untuk pilih file (JPG/PNG)</small>
          <small className="hint-dji">Foto DJI: GPS koordinat otomatis terbaca</small>
        </>
      )}
    </div>
  )
}
