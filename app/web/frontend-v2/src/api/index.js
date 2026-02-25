import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export const configApi = {
  get: () => api.get('/config'),
  update: (config) => api.put('/config', { config }),
}

export const taskApi = {
  startComment: () => api.post('/task/comment/start'),
  stopComment: () => api.post('/task/comment/stop'),
  commentStatus: () => api.get('/task/comment/status'),
  startWarmup: () => api.post('/task/warmup/start'),
  stopWarmup: () => api.post('/task/warmup/stop'),
  warmupStatus: () => api.get('/task/warmup/status'),
}

export const authApi = {
  status: () => api.get('/auth/status'),
  check: () => api.post('/auth/check'),
  startQrLogin: () => api.post('/auth/qrcode'),
  getQrImage: () => api.get('/auth/qrcode/image'),
}

export const fileApi = {
  browseExecutable: () => api.post('/file/browse/executable', null, { timeout: 120000 }),
  browseImage: () => api.post('/file/browse/image', null, { timeout: 120000 }),
}

export default api
