import axios from 'axios'

const BASE_URL = '/api'

const client = axios.create({ baseURL: BASE_URL, timeout: 30000 })

export const detectionApi = {
  checkHealth: async () => {
    const res = await client.get('/health')
    return res.data
  },

  detectSingle: async (file, params) => {
    const formData = new FormData()
    formData.append('file', file)
    const qs = params.toString()
    const res = await client.post(`/detect${qs ? '?' + qs : ''}`, formData)
    return res.data
  },

  detectBatch: async (files, params) => {
    const formData = new FormData()
    files.forEach(f => formData.append('files', f))
    const qs = params.toString()
    const res = await client.post(`/detect/batch${qs ? '?' + qs : ''}`, formData)
    return res.data
  },

  clearSession: async () => {
    const res = await client.post('/export/clear')
    return res.data
  },

  getExportUrl: () => `${BASE_URL}/export/csv`
}
