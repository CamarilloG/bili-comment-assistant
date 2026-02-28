<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const notifications = ref([])
let ws = null
let nextId = 0

onMounted(() => {
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/notifications`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('[Toast] WebSocket connected')
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      addNotification(data)
    } catch (e) {
      console.error('[Toast] Failed to parse notification:', e)
    }
  }

  ws.onerror = (error) => {
    console.error('[Toast] WebSocket error:', error)
  }

  ws.onclose = () => {
    console.log('[Toast] WebSocket closed, reconnecting in 3s...')
    setTimeout(connectWebSocket, 3000)
  }
}

function addNotification(data) {
  const id = nextId++
  const notification = {
    id,
    ...data,
  }

  notifications.value.unshift(notification)

  // 自动移除（根据类型设置不同的持续时间）
  const duration = data.type === 'captcha' || data.type === 'critical' ? 10000 : 5000
  setTimeout(() => {
    removeNotification(id)
  }, duration)
}

function removeNotification(id) {
  const index = notifications.value.findIndex(n => n.id === id)
  if (index !== -1) {
    notifications.value.splice(index, 1)
  }
}

function getTypeClass(type) {
  switch (type) {
    case 'error':
    case 'critical':
      return 'bg-red-500 text-white'
    case 'warning':
      return 'bg-yellow-500 text-white'
    case 'captcha':
      return 'bg-orange-500 text-white'
    case 'info':
    default:
      return 'bg-blue-500 text-white'
  }
}

function getIcon(type) {
  switch (type) {
    case 'error':
    case 'critical':
      return 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z'
    case 'warning':
      return 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z'
    case 'captcha':
      return 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z'
    case 'info':
    default:
      return 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
  }
}
</script>

<template>
  <div class="fixed top-4 right-4 z-50 space-y-2 pointer-events-none">
    <TransitionGroup name="toast">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        class="pointer-events-auto flex items-start gap-3 p-4 rounded-lg shadow-lg max-w-sm"
        :class="getTypeClass(notification.type)"
      >
        <svg class="w-6 h-6 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="getIcon(notification.type)" />
        </svg>
        <div class="flex-1 min-w-0">
          <p class="font-semibold text-sm">{{ notification.title }}</p>
          <p class="text-sm opacity-90 mt-1">{{ notification.message }}</p>
        </div>
        <button
          @click="removeNotification(notification.id)"
          class="flex-shrink-0 opacity-70 hover:opacity-100 transition-opacity"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.toast-move {
  transition: transform 0.3s ease;
}
</style>
