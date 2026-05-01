import axios from 'axios'

const BASE_URL = import.meta.env.PROD ? '/api' : 'http://localhost:8000'

/**
 * RescueVision Edge API Client
 */
export const detectionApi = {
  checkHealth: async () => {
    const res = await axios.get(`${BASE_URL}/health`)
    return res.data
  },

  detectSingle: async (file, params) => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await axios.post(`${BASE_URL}/detect?${params.toString()}`, formData)
    return res.data
  },

  detectBatch: async (files, params) => {
    const formData = new FormData()
    files.forEach(f => formData.append('files', f))
    const res = await axios.post(`${BASE_URL}/detect/batch?${params.toString()}`, formData)
    return res.data
  },

  clearSession: async () => {
    const res = await axios.post(`${BASE_URL}/export/clear`)
    return res.data
  },

  getExportUrl: () => `${BASE_URL}/export/csv`
}
