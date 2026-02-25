<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useConfigStore } from './stores/config'
import { useTaskStore } from './stores/task'
import AlertModal from './components/AlertModal.vue'

const configStore = useConfigStore()
const taskStore = useTaskStore()

const navItems = [
  { path: '/', label: '控制台', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0h4' },
  { path: '/comment', label: '评论设置', icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z' },
  { path: '/ai', label: 'AI 设置', icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' },
  { path: '/warmup', label: '养号设置', icon: 'M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z' },
  { path: '/settings', label: '基础设置', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' },
]

onMounted(() => {
  configStore.load()
  taskStore.startPolling()
  taskStore.connectLogs()
})

onUnmounted(() => {
  taskStore.stopPolling()
  taskStore.disconnectLogs()
})
</script>

<template>
  <div class="min-h-screen flex bg-gray-50 dark:bg-gray-950">
    <!-- Sidebar -->
    <aside class="w-56 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col shrink-0">
      <div class="px-5 py-5 border-b border-gray-200 dark:border-gray-800">
        <h1 class="text-lg font-bold tracking-tight">B站评论助手</h1>
        <p class="text-xs text-gray-500 mt-0.5">Web 控制面板</p>
      </div>
      <nav class="flex-1 py-3 space-y-0.5 px-2">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="$route.path === item.path
            ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
            : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'"
        >
          <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
          </svg>
          {{ item.label }}
        </router-link>
      </nav>
      <div class="px-4 py-3 border-t border-gray-200 dark:border-gray-800 text-xs text-gray-400">
        v2.2.0
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <header class="h-14 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex items-center px-6 shrink-0">
        <h2 class="text-base font-semibold">{{ $route.meta.title }}</h2>
        <div class="ml-auto flex items-center gap-3">
          <span
            class="text-xs px-2 py-0.5 rounded-full"
            :class="taskStore.commentStatus.running || taskStore.warmupStatus.running
              ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
              : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'"
          >
            {{ taskStore.commentStatus.running || taskStore.warmupStatus.running ? '任务运行中' : '空闲' }}
          </span>
        </div>
      </header>
      <div class="flex-1 overflow-y-auto p-6">
        <router-view />
      </div>
    </main>
    <AlertModal />
  </div>
</template>
