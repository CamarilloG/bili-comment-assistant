<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useConfigStore } from '../stores/config'

const configStore = useConfigStore()

const aiEnabled = ref(false)
const baseUrl = ref('https://api.deepseek.com/v1')
const apiKey = ref('')
const model = ref('deepseek-chat')
const aiTimeout = ref(30)
const maxRetries = ref(2)

const commentEnabled = ref(true)
const userIntent = ref('')
const commentStyle = ref('casual')
const maxLength = ref(100)
const minLength = ref(10)

const filterEnabled = ref(true)
const criteria = ref('')
const sensitivity = ref(50)

const testStatus = ref('')
const testing = ref(false)
const saving = ref(false)

const styleOptions = [
  { value: 'casual', label: '随意' },
  { value: 'enthusiastic', label: '热情' },
  { value: 'professional', label: '专业' },
]

const sensitivityLabel = computed(() => {
  const v = sensitivity.value
  if (v <= 20) return '极度宽松'
  if (v <= 40) return '宽松'
  if (v <= 60) return '平衡'
  if (v <= 80) return '严格'
  return '极度严格'
})

watch(() => configStore.config, (newConfig) => {
  if (newConfig?.ai) loadFromConfig(newConfig.ai)
}, { immediate: true })

function loadFromConfig(ai) {
  aiEnabled.value = ai.enabled || false
  baseUrl.value = ai.base_url || 'https://api.deepseek.com/v1'
  apiKey.value = ai.api_key || ''
  model.value = ai.model || 'deepseek-chat'
  aiTimeout.value = ai.timeout || 30
  maxRetries.value = ai.max_retries || 2

  const comment = ai.comment || {}
  commentEnabled.value = comment.enabled ?? true
  userIntent.value = comment.user_intent || ''
  commentStyle.value = comment.style || 'casual'
  maxLength.value = comment.max_length || 100
  minLength.value = comment.min_length || 10

  const filter = ai.filter || {}
  filterEnabled.value = filter.enabled ?? true
  criteria.value = filter.criteria || ''
  sensitivity.value = filter.sensitivity || 50
}

async function saveConfig() {
  saving.value = true
  try {
    await configStore.save({
      ai: {
        enabled: aiEnabled.value,
        base_url: baseUrl.value,
        api_key: apiKey.value,
        model: model.value,
        timeout: aiTimeout.value,
        max_retries: maxRetries.value,
        comment: {
          enabled: commentEnabled.value,
          user_intent: userIntent.value,
          style: commentStyle.value,
          max_length: maxLength.value,
          min_length: minLength.value,
        },
        filter: {
          enabled: filterEnabled.value,
          criteria: criteria.value,
          sensitivity: sensitivity.value,
        },
      },
    })
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  testing.value = true
  testStatus.value = '测试中...'
  try {
    const { default: axios } = await import('axios')
    const resp = await axios.post(
      `${baseUrl.value}/chat/completions`,
      { model: model.value, messages: [{ role: 'user', content: 'hi' }], max_tokens: 5 },
      { headers: { Authorization: `Bearer ${apiKey.value}` }, timeout: 10000 }
    )
    testStatus.value = resp.data?.choices?.length ? 'OK' : 'No response'
  } catch (e) {
    testStatus.value = `Error: ${e.message}`
  } finally {
    testing.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl space-y-5">
    <!-- API Connection -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">API 连接</h3>
      <label class="flex items-center gap-2 text-sm mb-4">
        <input type="checkbox" v-model="aiEnabled" class="accent-blue-600" /> 启用 AI 功能
      </label>
      <div class="space-y-3">
        <div>
          <label class="text-xs text-gray-500">Base URL</label>
          <input v-model="baseUrl" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-transparent" />
        </div>
        <div>
          <label class="text-xs text-gray-500">API Key</label>
          <input v-model="apiKey" type="password" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-transparent" />
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label class="text-xs text-gray-500">模型名称</label>
            <input v-model="model" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
          </div>
          <div>
            <label class="text-xs text-gray-500">超时(s)</label>
            <input v-model.number="aiTimeout" type="number" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
          </div>
          <div>
            <label class="text-xs text-gray-500">重试次数</label>
            <input v-model.number="maxRetries" type="number" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
          </div>
        </div>
        <div class="flex items-center gap-3 mt-2">
          <button @click="testConnection" :disabled="testing" class="text-sm px-4 py-1.5 rounded-lg border border-blue-500 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 disabled:opacity-50">
            {{ testing ? '测试中...' : '测试连接' }}
          </button>
          <span class="text-sm" :class="testStatus === 'OK' ? 'text-green-600' : 'text-gray-500'">{{ testStatus }}</span>
        </div>
      </div>
    </section>

    <!-- Smart Comment -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">智能评论</h3>
      <label class="flex items-center gap-2 text-sm mb-4">
        <input type="checkbox" v-model="commentEnabled" class="accent-blue-600" /> 启用智能评论
      </label>
      <div>
        <label class="text-xs text-gray-500">推广意图/人设</label>
        <textarea v-model="userIntent" rows="3" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-transparent resize-none" />
      </div>
      <div class="grid grid-cols-3 gap-3 mt-3">
        <div>
          <label class="text-xs text-gray-500">评论风格</label>
          <select v-model="commentStyle" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent">
            <option v-for="o in styleOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div>
          <label class="text-xs text-gray-500">最小字数</label>
          <input v-model.number="minLength" type="number" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
        <div>
          <label class="text-xs text-gray-500">最大字数</label>
          <input v-model.number="maxLength" type="number" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
      </div>
    </section>

    <!-- Smart Filter -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">智能筛选</h3>
      <label class="flex items-center gap-2 text-sm mb-4">
        <input type="checkbox" v-model="filterEnabled" class="accent-blue-600" /> 启用智能筛选
      </label>
      <div>
        <label class="text-xs text-gray-500">筛选标准</label>
        <textarea v-model="criteria" rows="3" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-transparent resize-none" />
      </div>
      <div class="mt-4">
        <div class="flex items-center justify-between mb-1">
          <label class="text-xs text-gray-500">无关敏感度</label>
          <span class="text-xs font-medium" :class="{
            'text-green-600': sensitivity <= 20,
            'text-blue-600': sensitivity > 20 && sensitivity <= 60,
            'text-orange-600': sensitivity > 60 && sensitivity <= 80,
            'text-red-600': sensitivity > 80,
          }">{{ sensitivity }} — {{ sensitivityLabel }}</span>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-xs text-gray-400 shrink-0">宽松</span>
          <input type="range" v-model.number="sensitivity" min="1" max="100" class="flex-1 accent-blue-600" />
          <span class="text-xs text-gray-400 shrink-0">严格</span>
        </div>
      </div>
    </section>

    <!-- Save -->
    <button
      @click="saveConfig"
      :disabled="saving"
      class="w-full py-2.5 rounded-xl text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 transition-colors"
    >
      {{ saving ? '保存中...' : '保存 AI 配置' }}
    </button>
  </div>
</template>
