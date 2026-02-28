import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

function slotParams(slot) {
  return { params: { slot: slot ?? '0' } }
}

export const configApi = {
  get: (slot) => api.get('/config', slotParams(slot)),
  update: (config, slot) => api.put('/config', { config }, slotParams(slot)),
}

export const taskApi = {
  /**
   * 启动评论任务。
   * mode: 'comment' | 'ai'
   */
  startComment: (slot, mode = 'comment') => api.post('/task/comment/start', { mode }, slotParams(slot)),
  stopComment: (slot) => api.post('/task/comment/stop', null, slotParams(slot)),
  commentStatus: (slot) => api.get('/task/comment/status', slotParams(slot)),
  startWarmup: (slot) => api.post('/task/warmup/start', null, slotParams(slot)),
  stopWarmup: (slot) => api.post('/task/warmup/stop', null, slotParams(slot)),
  warmupStatus: (slot) => api.get('/task/warmup/status', slotParams(slot)),
}

export const authApi = {
  status: (slot) => api.get('/auth/status', slotParams(slot)),
  check: (slot) => api.post('/auth/check', null, slotParams(slot)),
  startQrLogin: (slot) => api.post('/auth/qrcode', null, slotParams(slot)),
  getQrImage: (slot) => api.get('/auth/qrcode/image', slotParams(slot)),
}

export const fileApi = {
  browseExecutable: () => api.post('/file/browse/executable', null, { timeout: 120000 }),
  browseImage: () => api.post('/file/browse/image', null, { timeout: 120000 }),
}

export const instancesApi = {
  get: () => api.get('/instances'),
  add: () => api.post('/instances'),
  delete: (slotId) => api.delete(`/instances/${slotId}`),
}

export const modelsApi = {
  getList: () => api.get('/models'),
  test: (modelId) => api.post('/models/test', { model_id: modelId }),
}

export default api
