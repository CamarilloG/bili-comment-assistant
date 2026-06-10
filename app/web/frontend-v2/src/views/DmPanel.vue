<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useConfigStore } from '../stores/config'
import { useTaskStore } from '../stores/task'
import { useSlotStore } from '../stores/slot'
import { useAlertModalStore } from '../stores/alertModal'
import { taskApi } from '../api'

const configStore = useConfigStore()
const taskStore = useTaskStore()
const slotStore = useSlotStore()
const alertModal = useAlertModalStore()

const isDmRunning = computed(() => taskStore.isDmRunning)
const dmStats = computed(() => taskStore.dmStatus.stats || {})
const displayLogs = computed(() => taskStore.logsBySlot[slotStore.currentSlot] || [])
const starting = ref(false)

async function startDm() {
  if (isDmRunning.value || starting.value) return
  starting.value = true
  try {
    const resp = await taskApi.startDm(slotStore.currentSlot)
    if (resp?.data?.status === 'error') {
      alertModal.error('启动失败: ' + (resp.data.message || '未知错误'))
    }
    taskStore.pollDmStatus(slotStore.currentSlot)
  } catch (e) {
    alertModal.error('启动失败: ' + (e?.response?.data?.message || e?.message || String(e)))
  } finally {
    starting.value = false
  }
}

async function stopDm() {
  try {
    await taskApi.stopDm(slotStore.currentSlot)
  } catch (e) {
    alertModal.error('停止失败: ' + (e?.message || String(e)))
  }
}

const keywords = ref('')
const maxVideosPerKeyword = ref(5)
const order = ref('pubdate')
const duration = ref(0)
const strategy = ref('order')
const strictMatch = ref(false)
const skipHistory = ref(true)
const timeFilterType = ref('none')
const recentDays = ref(7)
const dateStart = ref('')
const dateEnd = ref('')
const maxCommentsPerVideo = ref(200)
const regexPatterns = ref('')
const useAi = ref(false)
const aiPrompt = ref('')
const dmTemplate = ref('')
const maxPerRun = ref(30)
const delayMin = ref(8)
const delayMax = ref(20)
const skipAlreadySent = ref(true)
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
  if (configStore.config?.dm_flow) loadFromConfig(configStore.config.dm_flow)
  watch(() => configStore.config?.dm_flow, (d) => { if (d) loadFromConfig(d) })
})

function loadFromConfig(d) {
  const s = d.search || {}
  keywords.value = (s.keywords || []).join('\n')
  maxVideosPerKeyword.value = s.max_videos_per_keyword || 5
  order.value = s.order || 'pubdate'
  duration.value = s.duration || 0
  strategy.value = s.strategy || 'order'
  strictMatch.value = s.strict_title_match || false
  skipHistory.value = s.skip_history ?? true
  const tr = s.time_range || {}
  timeFilterType.value = tr.type || 'none'
  if (tr.type === 'recent') recentDays.value = tr.value || 7
  if (tr.type === 'range' && tr.value) {
    dateStart.value = tr.value.start || ''
    dateEnd.value = tr.value.end || ''
  }
  maxCommentsPerVideo.value = (d.comment_scrape || {}).max_comments_per_video || 200

  const f = d.filter || {}
  regexPatterns.value = (f.regex_patterns || []).join('\n')
  useAi.value = f.use_ai || false
  aiPrompt.value = f.ai_prompt || ''

  const dm = d.dm || {}
  dmTemplate.value = dm.template || ''
  maxPerRun.value = dm.max_per_run || 30
  const dr = dm.delay_range || [8, 20]
  delayMin.value = dr[0] || 8
  delayMax.value = dr[1] || 20
  skipAlreadySent.value = dm.skip_already_sent ?? true
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
      dm_flow: {
        search: {
          keywords: keywords.value.split('\n').map(s => s.trim()).filter(Boolean),
          max_videos_per_keyword: Number(maxVideosPerKeyword.value),
          order: order.value,
          duration: Number(duration.value),
          time_range: buildTimeRange(),
          strategy: strategy.value,
          strict_title_match: strictMatch.value,
          skip_history: skipHistory.value,
        },
        comment_scrape: {
          max_comments_per_video: Number(maxCommentsPerVideo.value),
        },
        filter: {
          regex_patterns: regexPatterns.value.split('\n').map(s => s.trim()).filter(Boolean),
          use_ai: useAi.value,
          ai_prompt: aiPrompt.value,
        },
        dm: {
          template: dmTemplate.value,
          max_per_run: Number(maxPerRun.value),
          delay_range: [Number(delayMin.value), Number(delayMax.value)],
          skip_already_sent: skipAlreadySent.value,
        },
      },
    }, slotStore.currentSlot)
    alertModal.success('私信配置已保存')
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || String(e)
    alertModal.error('保存失败: ' + (Array.isArray(msg) ? msg.join(', ') : msg))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-3xl space-y-5">
    <!-- Search -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">搜索设置</h3>
      <div class="space-y-3">
        <div>
          <label class="text-xs text-gray-500">搜索关键词（每行一个）</label>
          <textarea v-model="keywords" rows="3" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" placeholder="每行输入一个关键词"></textarea>
        </div>
        <div>
          <label class="text-xs text-gray-500">每个关键词最大视频数</label>
          <input v-model.number="maxVideosPerKeyword" type="number" min="1" max="50" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
      </div>
    </section>

    <!-- Search Filters -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">搜索筛选</h3>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="text-xs text-gray-500">排序</label>
          <select v-model="order" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent">
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

    <!-- Comment Scrape -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">评论抓取</h3>
      <div>
        <label class="text-xs text-gray-500">每个视频最大评论抓取数</label>
        <input v-model.number="maxCommentsPerVideo" type="number" min="10" max="1000" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
      </div>
    </section>

    <!-- Filter -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">用户筛选</h3>
      <div class="space-y-3">
        <div>
          <label class="text-xs text-gray-500">正则匹配规则（每行一个，留空则不筛选）</label>
          <textarea v-model="regexPatterns" rows="3" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent font-mono" placeholder="例：想买|求推荐|哪里有"></textarea>
        </div>
        <div class="flex items-center justify-between">
          <div>
            <span class="text-sm font-medium">AI 智能筛选</span>
            <p class="text-xs text-gray-500">使用 AI 分析评论意图，进一步精筛目标用户</p>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="useAi" class="sr-only peer">
            <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 dark:peer-focus:ring-green-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-green-600"></div>
          </label>
        </div>
        <div v-if="useAi">
          <label class="text-xs text-gray-500">AI 筛选条件描述</label>
          <textarea v-model="aiPrompt" rows="2" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" placeholder="例：判断该评论者是否有购买意向"></textarea>
        </div>
      </div>
    </section>

    <!-- DM Settings -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">私信设置</h3>
      <div class="space-y-3">
        <div>
          <label class="text-xs text-gray-500">私信模板（支持 {'{uname}'} 变量）</label>
          <textarea v-model="dmTemplate" rows="3" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" placeholder="你好 {uname}，看到你的评论..."></textarea>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-xs text-gray-500">单次运行发送上限</label>
            <input v-model.number="maxPerRun" type="number" min="1" max="100" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
          </div>
          <div class="flex items-center gap-1.5 pt-5">
            <label class="flex items-center gap-1.5 text-sm"><input type="checkbox" v-model="skipAlreadySent" class="accent-green-600" /> 跳过已发送用户</label>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-xs text-gray-500">发送间隔最小值（秒）</label>
            <input v-model.number="delayMin" type="number" min="3" max="120" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
          </div>
          <div>
            <label class="text-xs text-gray-500">发送间隔最大值（秒）</label>
            <input v-model.number="delayMax" type="number" min="5" max="300" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
          </div>
        </div>
      </div>
    </section>

    <!-- Safety Note -->
    <section class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-4">
      <div class="flex items-start gap-2">
        <svg class="w-4 h-4 text-yellow-600 dark:text-yellow-400 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
        </svg>
        <div class="text-xs text-yellow-700 dark:text-yellow-300">
          <p class="font-medium mb-1">风控提示</p>
          <ul class="space-y-1 list-disc list-inside">
            <li>对陌生人每个账号只能发 1 条消息，对方回复或关注后才能继续</li>
            <li>建议每次运行发送上限 ≤ 30 条，间隔 ≥ 8 秒</li>
            <li>避免在模板中使用"微信""转账""加我"等敏感词</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Save -->
    <button
      @click="saveConfig"
      :disabled="saving"
      class="w-full py-2.5 rounded-xl text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 transition-colors"
    >
      {{ saving ? '保存中...' : '保存私信配置' }}
    </button>

    <!-- Task Controls -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">任务控制</h3>
      <div class="flex items-center gap-3 mb-4">
        <button
          @click="startDm"
          :disabled="isDmRunning || starting || taskStore.isAnyRunning"
          class="flex-1 py-2.5 rounded-xl text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {{ starting ? '启动中...' : isDmRunning ? '运行中...' : '开始私信任务' }}
        </button>
        <button
          @click="stopDm"
          :disabled="!isDmRunning"
          class="px-8 py-2.5 rounded-xl text-sm font-medium text-white bg-red-500 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          停止
        </button>
      </div>
      <!-- DM Stats -->
      <div v-if="isDmRunning || Object.keys(dmStats).length > 0" class="grid grid-cols-5 gap-2 text-center">
        <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-2">
          <div class="text-lg font-bold text-blue-600">{{ dmStats.total_scraped || 0 }}</div>
          <div class="text-xs text-gray-500">已抓取</div>
        </div>
        <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-2">
          <div class="text-lg font-bold text-purple-600">{{ dmStats.filtered || 0 }}</div>
          <div class="text-xs text-gray-500">已筛选</div>
        </div>
        <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-2">
          <div class="text-lg font-bold text-green-600">{{ dmStats.sent || 0 }}</div>
          <div class="text-xs text-gray-500">已发送</div>
        </div>
        <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-2">
          <div class="text-lg font-bold text-yellow-600">{{ dmStats.limited || 0 }}</div>
          <div class="text-xs text-gray-500">受限</div>
        </div>
        <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-2">
          <div class="text-lg font-bold text-red-600">{{ dmStats.failed || 0 }}</div>
          <div class="text-xs text-gray-500">失败</div>
        </div>
      </div>
    </section>

    <!-- Logs -->
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
