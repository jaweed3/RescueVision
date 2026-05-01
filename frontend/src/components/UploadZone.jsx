import { useRef, useState } from 'react'
import { extractFramesFromVideo, extractDJIMetadata } from '../utils/videoProcessor'
import './UploadZone.css'

const UploadIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="upload-svg">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
  </svg>
)

/**
 * UploadZone Component
 * Handles file selection (drag & drop or click) and triggers processing.
 */
export default function UploadZone({ onUpload, loading }) {
  const inputRef = useRef()
  const [dragging, setDragging] = useState(false)
  const [internalLoading, setInternalLoading] = useState(false)
  const [progress, setProgress] = useState(0)

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
          // Extract metadata if this is the first video in the selection
          if (!firstVideoMetadata) {
            firstVideoMetadata = await extractDJIMetadata(file)
          }
          // Process frames
          const frames = await extractFramesFromVideo(file, 1, 15)
          allFiles = [...allFiles, ...frames]
        } else {
          allFiles.push(file)
        }
      }
      
      onUpload(allFiles, firstVideoMetadata)
    } catch (err) {
      console.error('[UploadZone] File handling error:', err)
      alert(err.message || 'Error processing files.')
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
          <p>{internalLoading ? 'Processing Video...' : 'Uploading...'}</p>
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
