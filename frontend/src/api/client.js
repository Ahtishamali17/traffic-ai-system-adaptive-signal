import axios from 'axios'

// In dev, Vite proxies /api to the FastAPI backend (see vite.config.js).
// In production behind Nginx, /api is routed to the backend container.
const client = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

export const detectionApi = {
  uploadVideo: (file, onProgress) => {
    const form = new FormData()
    form.append('file', file)
    return client.post('/detection/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
    })
  },
  start: (payload) => client.post('/detection/start', payload),
  stop: (sessionId) => client.post(`/detection/stop/${sessionId}`),
  listSessions: () => client.get('/detection/sessions'),
  getSession: (sessionId) => client.get(`/detection/sessions/${sessionId}`),
  getCounts: (sessionId) => client.get(`/detection/sessions/${sessionId}/counts`),
  getViolations: (sessionId) => client.get(`/detection/sessions/${sessionId}/violations`),
  getSignals: (sessionId) => client.get(`/detection/sessions/${sessionId}/signals`),
  streamUrl: (sessionId) => `/api/v1/detection/stream/${sessionId}`,
}

export const analyticsApi = {
  getSummary: (params) => client.get('/analytics/summary', { params }),
}

export const complaintsApi = {
  classify: (text) => client.post('/complaints/classify', { text }),
  classifyBatch: (texts) => client.post('/complaints/classify-batch', { texts }),
  samples: () => client.get('/complaints/samples'),
  modelInfo: () => client.get('/complaints/model-info'),
}

export const reportsApi = {
  csvUrl: (params) => `/api/v1/reports/csv?${new URLSearchParams(params)}`,
  excelUrl: (params) => `/api/v1/reports/excel?${new URLSearchParams(params)}`,
  pdfUrl: (params) => `/api/v1/reports/pdf?${new URLSearchParams(params)}`,
}

export const healthApi = {
  check: () => axios.get('/api/health'),
}

export default client
