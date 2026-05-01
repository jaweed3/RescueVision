/**
 * Video Processing Utilities
 * Separates heavy browser-based video manipulation from UI components.
 */

export const extractFramesFromVideo = async (file, fps = 1, maxDuration = 15) => {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.src = URL.createObjectURL(file)
    
    video.onloadedmetadata = async () => {
      const duration = video.duration
      const actualDuration = Math.min(duration, maxDuration)
      const frames = []
      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const ctx = canvas.getContext('2d')

      for (let t = 0; t < actualDuration; t += 1/fps) {
        video.currentTime = t
        await new Promise(r => {
          video.addEventListener('seeked', r, { once: true })
        })
        
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
        const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.85))
        const frameFile = new File(
          [blob], 
          `${file.name.replace(/\.[^/.]+$/, "")}_t${t.toFixed(1)}.jpg`, 
          { type: 'image/jpeg' }
        )
        frames.push(frameFile)
      }
      URL.revokeObjectURL(video.src)
      resolve(frames)
    }
    
    video.onerror = () => reject(new Error('Format video tidak didukung atau rusak.'))
  })
}

export const extractDJIMetadata = async (file) => {
  try {
    const chunk = await file.slice(0, 500000).text()
    // DJI Drone specific XMP metadata tags
    const latMatch = chunk.match(/GpsLatitude="([+-]?\d+\.\d+)"/)
    const lonMatch = chunk.match(/GpsLongitude="([+-]?\d+\.\d+)"/)
    const altMatch = chunk.match(/RelativeAltitude="([+-]?\d+\.\d+)"/) || 
                     chunk.match(/AbsoluteAltitude="([+-]?\d+\.\d+)"/)
    
    if (latMatch && lonMatch) {
      return {
        lat: parseFloat(latMatch[1]),
        lon: parseFloat(lonMatch[1]),
        alt: altMatch ? parseFloat(altMatch[1]) : 80
      }
    }
  } catch (e) {
    console.error('[Processor] Metadata parse failed:', e)
  }
  return null
}
