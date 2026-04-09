import { useState, useEffect } from 'react'
import { detectionApi } from '../services/api'

/**
 * Custom hook to manage the RescueVision application state and business logic.
 */
export function useAppLogic() {
  const [singleResult, setSingleResult] = useState(null)
  const [batchResult, setBatchResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [manualGPS, setManualGPS] = useState({ lat: '', lon: '', alt: '80' })
  const [useManualGPS, setUseManualGPS] = useState(false)
  const [geolocating, setGeolocating] = useState(false)
  const [geoError, setGeoError] = useState(null)
  const [previewUrls, setPreviewUrls] = useState([])
  const [systemStatus, setSystemStatus] = useState(null)

  // System Health Polling
  useEffect(() => {
    const pollHealth = async () => {
      try {
        const data = await detectionApi.checkHealth()
        setSystemStatus(data)
      } catch {
        setSystemStatus({ status: 'error', model_loaded: false })
      }
    }
    pollHealth()
    const interval = setInterval(pollHealth, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleUpload = async (files, metadata = null) => {
    if (!files?.length) return
    setLoading(true)
    setError(null)

    // Cleanup old preview URLs
    previewUrls.forEach(URL.revokeObjectURL)
    const newUrls = files.map(f => URL.createObjectURL(f))
    setPreviewUrls(newUrls)

    // Apply metadata if present (from video extraction)
    if (metadata && metadata.lat && metadata.lon) {
      setManualGPS({
        lat: metadata.lat.toString(),
        lon: metadata.lon.toString(),
        alt: (metadata.alt || 80).toString()
      })
      setUseManualGPS(true)
    }

    const params = new URLSearchParams()
    if ((useManualGPS || metadata) && (metadata?.lat || manualGPS.lat)) {
      params.append('manual_lat', metadata?.lat || manualGPS.lat)
      params.append('manual_lon', metadata?.lon || manualGPS.lon)
      params.append('manual_altitude', metadata?.alt || manualGPS.alt || '80')
    }

    try {
      if (files.length === 1) {
        const data = await detectionApi.detectSingle(files[0], params)
        setSingleResult(data)
        setBatchResult(null)
      } else {
        const data = await detectionApi.detectBatch(files, params)
        setBatchResult(data)
        setSingleResult(null)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Detection failed. Check backend connectivity.')
    } finally {
      setLoading(false)
    }
  }

  const handleDeviceGPS = () => {
    if (!navigator.geolocation) {
      setGeoError('Geolocation not supported by this browser.')
      return
    }
    setGeolocating(true)
    setGeoError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude, altitude } = pos.coords
        setManualGPS({
          lat: latitude.toFixed(6),
          lon: longitude.toFixed(6),
          alt: altitude ? altitude.toFixed(1) : '80'
        })
        setUseManualGPS(true)
        setGeolocating(false)
      },
      (err) => {
        setGeoError(`GPS Error: ${err.message}`)
        setGeolocating(false)
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    )
  }

  const handleClear = async () => {
    if (window.confirm('Clear all server-side detection logs?')) {
      try {
        await detectionApi.clearSession()
        setSingleResult(null)
        setBatchResult(null)
      } catch (err) {
        console.error('Failed to clear session:', err)
      }
    }
  }

  const results = batchResult ? batchResult.results : (singleResult ? [singleResult] : [])
  const allDetections = results.flatMap((r) => r.detections)

  const stats = {
    victims: batchResult ? batchResult.total_victims : (singleResult?.total_victims || 0),
    images: batchResult ? batchResult.total_images : (singleResult ? 1 : 0),
    inference: batchResult 
      ? (batchResult.results.reduce((s, r) => s + r.inference_ms, 0) / batchResult.total_images).toFixed(1)
      : singleResult?.inference_ms || 0,
    gps: singleResult ? singleResult.gps_source.toUpperCase() : (batchResult ? 'MIXED' : '-')
  }

  return {
    state: {
      singleResult, batchResult, loading, error, manualGPS, useManualGPS,
      geolocating, geoError, previewUrls, systemStatus, results, allDetections, stats
    },
    actions: {
      handleUpload, handleDeviceGPS, handleClear, setUseManualGPS, setManualGPS,
      handleExport: () => window.open(detectionApi.getExportUrl(), '_blank')
    }
  }
}
