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
  const dmStatus = ref({ running: false, status: 'idle', stats: {} })
  const logsBySlot = ref({})
  const logs = ref([])

  const isCommentRunning = computed(() => commentStatus.value.running)
  const isWarmupRunning = computed(() => warmupStatus.value.running)
  const isDmRunning = computed(() => dmStatus.value.running)
  const isAnyRunning = computed(() => isCommentRunning.value || isWarmupRunning.value || isDmRunning.value)
  const displayStatus = computed(() => {
    if (isCommentRunning.value) return statusToLabel(commentStatus.value.status)
    if (isWarmupRunning.value) return statusToLabel(warmupStatus.value.status)
    if (isDmRunning.value) return statusToLabel(dmStatus.value.status)
    return ''
  })

  let pollTimer = null
  let ws = null
  let pollingSlot = '0'
  let currentLogSlot = '0'

  async function pollCommentStatus(slot = '0') {
    try {
      const { data } = await taskApi.commentStatus(slot)
      commentStatus.value = data
    } catch { /* ignore */ }
  }

  async function pollWarmupStatus(slot = '0') {
    try {
      const { data } = await taskApi.warmupStatus(slot)
      warmupStatus.value = data
    } catch { /* ignore */ }
  }

  async function pollDmStatus(slot = '0') {
    try {
      const { data } = await taskApi.dmStatus(slot)
      dmStatus.value = data
    } catch { /* ignore */ }
  }

  function startPolling(slot = '0') {
    stopPolling()
    pollingSlot = slot
    pollTimer = setInterval(() => {
      pollCommentStatus(pollingSlot)
      pollWarmupStatus(pollingSlot)
      pollDmStatus(pollingSlot)
    }, 2000)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function connectLogs(slot = '0') {
    if (ws) { ws.onclose = null; ws.close(); ws = null }
    currentLogSlot = slot
    if (!logsBySlot.value[slot]) logsBySlot.value[slot] = []
    const targetSlot = slot
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    ws = new WebSocket(`${proto}://${location.host}/ws/logs?slot=${encodeURIComponent(slot)}`)
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
      const arr = logsBySlot.value[targetSlot] || []
      arr.unshift(entry)
      if (arr.length > 500) arr.pop()
    }
    ws.onclose = () => {
      setTimeout(() => connectLogs(currentLogSlot), 3000)
    }
  }

  function disconnectLogs() {
    if (ws) { ws.onclose = null; ws.close(); ws = null }
  }

  function setLogsForCurrentSlot(slot) {
    logs.value = logsBySlot.value[slot] || []
  }

  return {
    commentStatus, warmupStatus, dmStatus, logs, logsBySlot,
    setLogsForCurrentSlot,
    isCommentRunning, isWarmupRunning, isDmRunning, isAnyRunning, displayStatus,
    pollCommentStatus, pollWarmupStatus, pollDmStatus,
    startPolling, stopPolling,
    connectLogs, disconnectLogs,
  }
})
