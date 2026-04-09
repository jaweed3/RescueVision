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
  const [internalLoading, setInternalLoading] = useState(false)
  const [progress, setProgress] = useState(0)

  const extractFramesFromVideo = async (file) => {
    return new Promise((resolve, reject) => {
      const video = document.createElement('video')
      video.preload = 'metadata'
      video.src = URL.createObjectURL(file)
      
      video.onloadedmetadata = async () => {
        const duration = video.duration
        const maxDuration = 15
        const actualDuration = Math.min(duration, maxDuration)
        const frames = []
        const canvas = document.createElement('canvas')
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
        const ctx = canvas.getContext('2d')

        for (let t = 0; t < actualDuration; t++) {
          video.currentTime = t
          await new Promise(r => {
            video.addEventListener('seeked', r, { once: true })
          })
          
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
          const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.85))
          const frameFile = new File([blob], `${file.name.replace(/\.[^/.]+$/, "")}_frame_${t}.jpg`, { type: 'image/jpeg' })
          frames.push(frameFile)
          setProgress(Math.round(((t + 1) / actualDuration) * 100))
        }
        URL.revokeObjectURL(video.src)
        resolve(frames)
      }
      
      video.onerror = () => reject(new Error('Format video tidak didukung atau rusak.'))
    })
  }

  const extractDJIMetadata = async (file) => {
    try {
      const chunk = await file.slice(0, 500000).text()
      // DJI Drone specific XMP metadata tags
      const latMatch = chunk.match(/GpsLatitude="([+-]?\d+\.\d+)"/)
      const lonMatch = chunk.match(/GpsLongitude="([+-]?\d+\.\d+)"/)
      const altMatch = chunk.match(/RelativeAltitude="([+-]?\d+\.\d+)"/) || chunk.match(/AbsoluteAltitude="([+-]?\d+\.\d+)"/)
      
      if (latMatch && lonMatch) {
        return {
          lat: parseFloat(latMatch[1]),
          lon: parseFloat(lonMatch[1]),
          alt: altMatch ? parseFloat(altMatch[1]) : 80
        }
      }
    } catch (e) {
      console.warn('Metadata parse failed:', e)
    }
    return null
  }

  const handleFiles = async (fileList) => {
    const files = Array.from(fileList || [])
    if (!files.length) return

    setInternalLoading(true)
    setProgress(0)
    
    try {
      let allFiles = []
      let firstVideoMetadata = null
      for (const file of files) {
        if (file.type.startsWith('video/')) {
          if (!firstVideoMetadata) {
            firstVideoMetadata = await extractDJIMetadata(file)
          }
          const frames = await extractFramesFromVideo(file)
          allFiles = [...allFiles, ...frames]
        } else {
          allFiles.push(file)
        }
      }
      onUpload(allFiles, firstVideoMetadata)
    } catch (err) {
      alert(err.message)
    } finally {
      setInternalLoading(false)
      setProgress(0)
    }
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  const isActuallyLoading = loading || internalLoading

  return (
    <div
      className={`upload-zone ${dragging ? 'drag' : ''} ${isActuallyLoading ? 'loading' : ''}`}
      onClick={() => !isActuallyLoading && inputRef.current.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/*,video/*"
        style={{ display: 'none' }}
        onChange={e => handleFiles(e.target.files)}
      />
      {isActuallyLoading ? (
        <div className="upload-loading">
          <div className="mini-spinner" />
          <p>{internalLoading ? `Sampling Video (${progress}%)...` : 'Memproses file...'}</p>
        </div>
      ) : (
        <>
          <div className="icon-circle">
            <UploadIcon />
          </div>
          <div className="text-content">
            <p className="main-text">Drag & drop foto/video drone</p>
            <p className="sub-text">Mendukung JPG, PNG, dan Video (max 15s)</p>
          </div>
          <div className="dji-hint">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '12px' }}>
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <span>Auto-sampling 1 FPS + EXIF detect</span>
          </div>
        </>
      )}
    </div>
  )
}
