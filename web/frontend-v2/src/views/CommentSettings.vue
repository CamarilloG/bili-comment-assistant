<script setup>
import { ref, onMounted, watch } from 'vue'
import { useConfigStore } from '../stores/config'
import { fileApi } from '../api'

const configStore = useConfigStore()

const keywords = ref('')
const commentText = ref('')
const enableImage = ref(false)
const imagePath = ref('')
const minDelay = ref(5)
const maxDelay = ref(15)
const timeout = ref(30000)
const maxVideos = ref(5)
const sortOrder = ref('totalrank')
const duration = ref(0)
const strategy = ref('order')
const strictMatch = ref(false)
const skipHistory = ref(true)
const timeFilterType = ref('none')
const recentDays = ref(7)
const dateStart = ref('')
const dateEnd = ref('')

const browsingImg = ref(false)
const saving = ref(false)

const sortOptions = [
  { value: 'totalrank', label: '综合排序' },
  { value: 'pubdate', label: '最新发布' },
  { value: 'click', label: '最多播放' },
  { value: 'dm', label: '最多弹幕' },
  { value: 'stow', label: '最多收藏' },
]
const durationOptions = [
  { value: 0, label: '全部时长' },
  { value: 1, label: '10分钟以下' },
  { value: 2, label: '10-30分钟' },
  { value: 3, label: '30-60分钟' },
  { value: 4, label: '60分钟以上' },
]

onMounted(() => {
  if (configStore.config) loadFromConfig(configStore.config)
  else watch(() => configStore.config, (c) => { if (c) loadFromConfig(c) }, { once: true })
})

function loadFromConfig(c) {
  keywords.value = (c.search?.keywords || []).join(', ')
  commentText.value = (c.comment?.texts || [])[0] || ''
  enableImage.value = c.comment?.enable_image || false
  imagePath.value = (c.comment?.images || [])[0] || ''
  minDelay.value = c.behavior?.min_delay || 5
  maxDelay.value = c.behavior?.max_delay || 15
  timeout.value = c.behavior?.timeout || 30000
  maxVideos.value = c.search?.max_videos_per_keyword || 5
  sortOrder.value = c.search?.filter?.sort || 'totalrank'
  duration.value = c.search?.filter?.duration || 0
  strategy.value = c.search?.strategy?.selection || 'order'
  strictMatch.value = c.search?.strategy?.strict_title_match || false
  skipHistory.value = c.account?.skip_history ?? true
  const tr = c.search?.filter?.time_range || {}
  timeFilterType.value = tr.type || 'none'
  if (tr.type === 'recent') recentDays.value = tr.value || 7
  if (tr.type === 'range' && tr.value) {
    dateStart.value = tr.value.start || ''
    dateEnd.value = tr.value.end || ''
  }
}

function buildTimeRange() {
  if (timeFilterType.value === 'recent') return { type: 'recent', value: Number(recentDays.value) }
  if (timeFilterType.value === 'range') return { type: 'range', value: { start: dateStart.value, end: dateEnd.value } }
  return { type: 'none', value: null }
}

async function saveConfig() {
  saving.value = true
  try {
    await configStore.save({
      account: { cookie_file: 'cookies.json', skip_history: skipHistory.value },
      search: {
        keywords: keywords.value.split(',').map(k => k.trim()).filter(Boolean),
        max_videos_per_keyword: Number(maxVideos.value),
        filter: { sort: sortOrder.value, duration: Number(duration.value), time_range: buildTimeRange() },
        strategy: { selection: strategy.value, strict_title_match: strictMatch.value, random_pool_size: 20 },
      },
      comment: {
        texts: [commentText.value],
        enable_image: enableImage.value,
        images: imagePath.value ? [imagePath.value] : [],
      },
      behavior: {
        min_delay: Number(minDelay.value),
        max_delay: Number(maxDelay.value),
        timeout: Number(timeout.value),
      },
    })
  } finally {
    saving.value = false
  }
}

async function browseImage() {
  browsingImg.value = true
  try {
    const { data } = await fileApi.browseImage()
    if (data.path) imagePath.value = data.path
  } catch { /* cancelled */ }
  browsingImg.value = false
}
</script>

<template>
  <div class="max-w-2xl space-y-5">
    <!-- Keywords & Comment -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">评论内容</h3>
      <label class="block text-xs text-gray-500 mb-1">搜索关键词 (逗号分隔)</label>
      <input v-model="keywords" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-transparent focus:ring-2 focus:ring-blue-500 outline-none" />

      <label class="block text-xs text-gray-500 mt-3 mb-1">评论内容</label>
      <textarea v-model="commentText" rows="3" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-transparent focus:ring-2 focus:ring-blue-500 outline-none resize-none" />

      <div class="mt-3">
        <label class="flex items-center gap-1.5 text-sm mb-1.5">
          <input type="checkbox" v-model="enableImage" class="accent-blue-600" /> 启用图片
        </label>
        <div class="flex gap-2">
          <input v-model="imagePath" placeholder="图片路径" class="flex-1 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
          <button @click="browseImage" :disabled="browsingImg"
            class="shrink-0 px-3 py-1.5 text-xs rounded-lg border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50">
            {{ browsingImg ? '...' : '选择' }}
          </button>
        </div>
      </div>
    </section>

    <!-- Run Parameters -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">运行参数</h3>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="text-xs text-gray-500">最小间隔(s)</label>
          <input v-model.number="minDelay" type="number" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
        <div>
          <label class="text-xs text-gray-500">最大间隔(s)</label>
          <input v-model.number="maxDelay" type="number" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
        <div>
          <label class="text-xs text-gray-500">最大评论数</label>
          <input v-model.number="maxVideos" type="number" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
        <div>
          <label class="text-xs text-gray-500">超时(ms)</label>
          <input v-model.number="timeout" type="number" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
      </div>
    </section>

    <!-- Search Filters -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">搜索筛选</h3>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="text-xs text-gray-500">排序</label>
          <select v-model="sortOrder" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent">
            <option v-for="o in sortOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div>
          <label class="text-xs text-gray-500">时长</label>
          <select v-model.number="duration" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent">
            <option v-for="o in durationOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div>
          <label class="text-xs text-gray-500">选择策略</label>
          <select v-model="strategy" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent">
            <option value="order">顺序选择</option>
            <option value="random">随机选择</option>
          </select>
        </div>
        <div>
          <label class="text-xs text-gray-500">时间限制</label>
          <select v-model="timeFilterType" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent">
            <option value="none">不限制</option>
            <option value="recent">近几天</option>
            <option value="range">指定日期范围</option>
          </select>
        </div>
      </div>

      <div v-if="timeFilterType === 'recent'" class="mt-3 flex items-center gap-2">
        <span class="text-xs text-gray-500">最近</span>
        <input v-model.number="recentDays" type="number" min="1" class="w-20 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        <span class="text-xs text-gray-500">天</span>
      </div>
      <div v-if="timeFilterType === 'range'" class="mt-3 flex items-center gap-2">
        <input v-model="dateStart" type="date" class="flex-1 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        <span class="text-xs text-gray-400">至</span>
        <input v-model="dateEnd" type="date" class="flex-1 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
      </div>

      <div class="flex items-center gap-4 mt-3">
        <label class="flex items-center gap-1.5 text-sm">
          <input type="checkbox" v-model="strictMatch" class="accent-blue-600" /> 严格匹配
        </label>
        <label class="flex items-center gap-1.5 text-sm">
          <input type="checkbox" v-model="skipHistory" class="accent-blue-600" /> 跳过历史
        </label>
      </div>
    </section>

    <!-- Save -->
    <button
      @click="saveConfig"
      :disabled="saving"
      class="w-full py-2.5 rounded-xl text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors"
    >
      {{ saving ? '保存中...' : '保存评论配置' }}
    </button>
  </div>
</template>
