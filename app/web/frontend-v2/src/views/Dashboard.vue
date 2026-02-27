<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useConfigStore } from '../stores/config'
import { useTaskStore } from '../stores/task'
import { useSlotStore } from '../stores/slot'
import { taskApi, authApi } from '../api'

const router = useRouter()
const configStore = useConfigStore()
const taskStore = useTaskStore()
const slotStore = useSlotStore()

const mode = ref('comment')
const loginStatus = ref(null)

const isCommentRunning = computed(() => taskStore.isCommentRunning)
const isWarmupRunning = computed(() => taskStore.isWarmupRunning)
const isAnyRunning = computed(() => taskStore.isAnyRunning)
const videos = computed(() => taskStore.commentStatus.videos || [])
// 直接使用当前实例的日志数组，避免 setLogsForCurrentSlot 与 WS 写入不同步导致不更新
const displayLogs = computed(() => taskStore.logsBySlot[slotStore.currentSlot] || [])

watch(() => configStore.config, (c) => {
  if (!c) return
  checkAuth()
}, { immediate: true })

watch(() => slotStore.currentSlot, () => {
  checkAuth()
})

async function checkAuth() {
  try {
    const { data } = await authApi.status(slotStore.currentSlot)
    loginStatus.value = data.logged_in
  } catch { loginStatus.value = null }
}

async function startTask() {
  if (isAnyRunning.value) return
  const slot = slotStore.currentSlot

  if (mode.value === 'comment') {
    // 普通评论模式：仅使用模板评论与普通图片配置
    await taskApi.startComment(slot, 'comment')
  } else if (mode.value === 'ai_comment') {
    // AI 增强模式：评论与图片由 AI 配置接管，可选启用智能筛选
    await taskApi.startComment(slot, 'ai')
  } else if (mode.value === 'warmup') {
    await taskApi.startWarmup(slot)
  }

  taskStore.pollCommentStatus(slot)
  taskStore.pollWarmupStatus(slot)
}

async function stopTask() {
  const slot = slotStore.currentSlot
  if (mode.value === 'warmup') {
    await taskApi.stopWarmup(slot)
  } else {
    await taskApi.stopComment(slot)
  }
}

const modes = [
  { value: 'comment', label: '普通评论', desc: '使用模板评论内容', color: 'blue' },
  { value: 'ai_comment', label: 'AI 评论', desc: 'AI 智能生成评论', color: 'purple' },
  { value: 'warmup', label: '养号模式', desc: '模拟正常浏览行为', color: 'orange' },
]
</script>

<template>
  <div class="space-y-6">
    <!-- Status Bar -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span
          class="text-xs px-2.5 py-1 rounded-full font-medium"
          :class="isAnyRunning
            ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
            : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'"
        >
          {{ isAnyRunning ? '任务运行中' : '空闲' }}
        </span>
        <span v-if="isAnyRunning && taskStore.displayStatus" class="text-xs text-gray-500">{{ taskStore.displayStatus }}</span>
      </div>
      <div class="flex items-center gap-2">
        <span
          class="text-xs px-2 py-0.5 rounded-full cursor-pointer"
          :class="loginStatus === true ? 'bg-green-100 text-green-700' : loginStatus === false ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'"
          @click="router.push('/settings')"
          title="点击前往登录设置"
        >
          {{ loginStatus === true ? '已登录' : loginStatus === false ? '未登录' : '未检测' }}
        </span>
      </div>
    </div>

    <!-- Mode Selector -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">启动模式</h3>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <label
          v-for="m in modes" :key="m.value"
          class="relative flex flex-col gap-1 p-4 rounded-xl border-2 cursor-pointer transition-all"
          :class="mode === m.value
            ? (m.color === 'blue' ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : m.color === 'purple' ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20' : 'border-orange-500 bg-orange-50 dark:bg-orange-900/20')
            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'"
        >
          <input type="radio" v-model="mode" :value="m.value" class="sr-only" />
          <span class="text-sm font-semibold">{{ m.label }}</span>
          <span class="text-xs text-gray-500">{{ m.desc }}</span>
        </label>
      </div>

      <!-- Action Buttons -->
      <div class="flex gap-3 mt-5">
        <button
          @click="startTask"
          :disabled="isAnyRunning"
          class="flex-1 py-2.5 rounded-xl text-sm font-medium text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          :class="mode === 'warmup' ? 'bg-orange-500 hover:bg-orange-600' : mode === 'ai_comment' ? 'bg-purple-600 hover:bg-purple-700' : 'bg-blue-600 hover:bg-blue-700'"
        >
          {{ isAnyRunning ? '运行中...' : '开始任务' }}
        </button>
        <button
          @click="stopTask"
          :disabled="!isAnyRunning"
          class="px-8 py-2.5 rounded-xl text-sm font-medium text-white bg-red-500 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          停止
        </button>
      </div>
    </section>

    <!-- Video List：序号、评论内容、评论类型，新项顶置，横向滚动 -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-3">
        视频处理列表
        <span class="text-gray-400 font-normal">({{ videos.length }})</span>
      </h3>
      <div class="overflow-x-auto overflow-y-auto max-h-72">
        <table class="text-sm min-w-[800px] w-full">
          <thead class="text-left text-xs text-gray-500 uppercase border-b dark:border-gray-800 sticky top-0 bg-white dark:bg-gray-900 z-10">
            <tr>
              <th class="py-2 pr-3 whitespace-nowrap">序号</th>
              <th class="py-2 pr-3 whitespace-nowrap">BV号</th>
              <th class="py-2 pr-3 whitespace-nowrap">标题</th>
              <th class="py-2 pr-3 whitespace-nowrap">UP主</th>
              <th class="py-2 pr-3 whitespace-nowrap">播放</th>
              <th class="py-2 pr-3 whitespace-nowrap">状态</th>
              <th class="py-2 pr-3 whitespace-nowrap">评论内容</th>
              <th class="py-2 pr-3 whitespace-nowrap">评论类型</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(v, idx) in videos" :key="v.bv + '-' + idx" class="border-b dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/40">
              <td class="py-2 pr-3 text-gray-500">{{ idx + 1 }}</td>
              <td class="py-2 pr-3 text-xs text-gray-500 font-mono whitespace-nowrap">{{ v.bv }}</td>
              <td class="py-2 pr-3 max-w-[200px] truncate" :title="v.title">{{ v.title }}</td>
              <td class="py-2 pr-3 text-gray-600 dark:text-gray-400 whitespace-nowrap">{{ v.author }}</td>
              <td class="py-2 pr-3 text-gray-500 whitespace-nowrap">{{ v.views }}</td>
              <td class="py-2 pr-3 whitespace-nowrap">
                <span
                  class="text-xs px-2 py-0.5 rounded-full"
                  :class="{
                    'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300': v.status === '成功',
                    'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300': v.status === '失败',
                    'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300': v.status === '处理中...',
                    'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400': !['成功','失败','处理中...'].includes(v.status),
                  }"
                >{{ v.status }}</span>
              </td>
              <td class="py-2 pr-3 max-w-[220px] truncate text-gray-700 dark:text-gray-300" :title="v.comment_content">{{ v.comment_content || '—' }}</td>
              <td class="py-2 pr-3 whitespace-nowrap">{{ v.comment_type === 'AI' ? 'AI' : (v.comment_type === 'Template' ? '模板' : (v.comment_type || '—')) }}</td>
            </tr>
            <tr v-if="videos.length === 0">
              <td colspan="8" class="py-8 text-center text-gray-400 text-sm">暂无数据，选择模式并点击开始</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Logs：新消息顶置，按字段着色 -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-3">运行日志</h3>
      <div class="bg-gray-950 font-mono text-xs rounded-lg p-3 h-56 overflow-y-auto flex flex-col">
        <div v-for="(entry, i) in displayLogs" :key="i" class="leading-5 flex gap-2 flex-shrink-0">
          <span class="text-gray-500 flex-shrink-0">{{ entry.time }}</span>
          <span
            class="flex-shrink-0 font-medium w-14"
            :class="{
              'text-green-400': entry.level === 'INFO',
              'text-yellow-400': entry.level === 'WARNING',
              'text-red-400': entry.level === 'ERROR',
              'text-cyan-400': entry.level === 'DEBUG',
              'text-gray-400': !['INFO','WARNING','ERROR','DEBUG'].includes(entry.level),
            }"
          >{{ entry.level }}</span>
          <span class="text-gray-300 break-words min-w-0">{{ entry.message }}</span>
        </div>
        <div v-if="displayLogs.length === 0" class="text-gray-600">等待日志输出...</div>
      </div>
    </section>
  </div>
</template>
