import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { taskApi } from '../api'

const STATUS_LABELS = {
  starting: '启动中',
  running: '运行中',
  completed: '已完成',
  idle: '',
}
function statusToLabel(s) {
  if (!s || s === 'idle') return ''
  if (STATUS_LABELS[s]) return STATUS_LABELS[s]
  if (typeof s === 'string' && s.startsWith('error:')) return '错误'
  return s
}

export const useTaskStore = defineStore('task', () => {
  const commentStatus = ref({ running: false, status: 'idle', videos: [], video_count: 0 })
  const warmupStatus = ref({ running: false, status: 'idle', stats: {} })
  const logs = ref([])

  const isCommentRunning = computed(() => commentStatus.value.running)
  const isWarmupRunning = computed(() => warmupStatus.value.running)
  const isAnyRunning = computed(() => isCommentRunning.value || isWarmupRunning.value)
  const displayStatus = computed(() => {
    if (isCommentRunning.value) return statusToLabel(commentStatus.value.status)
    if (isWarmupRunning.value) return statusToLabel(warmupStatus.value.status)
    return ''
  })

  let pollTimer = null
  let ws = null

  async function pollCommentStatus() {
    try {
      const { data } = await taskApi.commentStatus()
      commentStatus.value = data
    } catch { /* ignore */ }
  }

  async function pollWarmupStatus() {
    try {
      const { data } = await taskApi.warmupStatus()
      warmupStatus.value = data
    } catch { /* ignore */ }
  }

  function startPolling() {
    stopPolling()
    pollTimer = setInterval(() => {
      pollCommentStatus()
      pollWarmupStatus()
    }, 2000)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function connectLogs() {
    if (ws) ws.close()
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    ws = new WebSocket(`${proto}://${location.host}/ws/logs`)
    ws.onmessage = (e) => {
      let entry
      const raw = e.data
      try {
        entry = JSON.parse(raw)
        if (!entry || typeof entry.message === 'undefined') entry = null
      } catch {
        entry = null
      }
      if (!entry) {
        const s = String(raw)
        const i1 = s.indexOf('\t')
        const i2 = i1 >= 0 ? s.indexOf('\t', i1 + 1) : -1
        if (i1 >= 0 && i2 >= 0) {
          entry = { time: s.slice(0, i1), level: s.slice(i1 + 1, i2), message: s.slice(i2 + 1) }
        } else {
          entry = { time: '', level: 'INFO', message: raw }
        }
      }
      logs.value.unshift(entry)
      if (logs.value.length > 500) logs.value.pop()
    }
    ws.onclose = () => {
      setTimeout(connectLogs, 3000)
    }
  }

  function disconnectLogs() {
    if (ws) { ws.onclose = null; ws.close(); ws = null }
  }

  return {
    commentStatus, warmupStatus, logs,
    isCommentRunning, isWarmupRunning, isAnyRunning, displayStatus,
    pollCommentStatus, pollWarmupStatus,
    startPolling, stopPolling,
    connectLogs, disconnectLogs,
  }
})
