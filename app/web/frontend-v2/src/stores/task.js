import { defineStore } from 'pinia'
import { ref } from 'vue'
import { taskApi } from '../api'

export const useTaskStore = defineStore('task', () => {
  const commentStatus = ref({ running: false, status: 'idle', videos: [], video_count: 0 })
  const warmupStatus = ref({ running: false, status: 'idle', stats: {} })
  const logs = ref([])

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
      try {
        entry = JSON.parse(e.data)
        if (!entry || typeof entry.message === 'undefined') entry = { time: '', level: 'INFO', message: e.data }
      } catch {
        entry = { time: '', level: 'INFO', message: e.data }
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
    pollCommentStatus, pollWarmupStatus,
    startPolling, stopPolling,
    connectLogs, disconnectLogs,
  }
})
