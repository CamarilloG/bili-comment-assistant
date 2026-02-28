<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useConfigStore } from '../stores/config'
import { useSlotStore } from '../stores/slot'
import { useAlertModalStore } from '../stores/alertModal'
import { fileApi, modelsApi } from '../api'

const configStore = useConfigStore()
const slotStore = useSlotStore()
const alertModal = useAlertModalStore()

const modelList = ref([])
const modelId = ref('deepseek_chat')
const aiTimeout = ref(30)
const maxRetries = ref(2)

const commentEnabled = ref(true)
const maxComments = ref(10)
const maxRelated = ref(5)
const userIntent = ref('')
const commentStyle = ref('casual')
const maxLength = ref(100)
const minLength = ref(10)
const commentEnableImage = ref(false)
const commentImagePath = ref('')

const filterEnabled = ref(true)
const criteria = ref('')
const sensitivity = ref(50)
const useComments = ref(false)
const useRelated = ref(false)

const browsingImage = ref(false)
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

onMounted(async () => {
  if (!configStore.config) configStore.load(slotStore.currentSlot)
  try {
    const { data } = await modelsApi.getList()
    modelList.value = data?.models || []
    if (modelList.value.length && !modelId.value) modelId.value = modelList.value[0].id
  } catch (_) {}
  watch(
    () => configStore.config?.ai,
    (ai) => { if (ai) loadFromConfig(ai) },
    { immediate: true }
  )
})

function loadFromConfig(ai) {
  modelId.value = ai.model_id || 'deepseek_chat'
  aiTimeout.value = ai.timeout ?? 30
  maxRetries.value = ai.max_retries ?? 2

  const comment = ai.comment || {}
  commentEnabled.value = comment.enabled ?? true
  maxComments.value = comment.max_comments ?? 10
  maxRelated.value = comment.max_related ?? 5
  userIntent.value = comment.user_intent || ''
  commentStyle.value = comment.style || 'casual'
  maxLength.value = comment.max_length || 100
  minLength.value = comment.min_length || 10
  commentEnableImage.value = comment.enable_image ?? false
  commentImagePath.value = (comment.images || [])[0] || ''

  const filter = ai.filter || {}
  filterEnabled.value = filter.enabled ?? true
  criteria.value = filter.criteria || ''
  sensitivity.value = filter.sensitivity || 50
  useComments.value = filter.use_comments ?? false
  useRelated.value = filter.use_related ?? false
}

async function saveConfig() {
  saving.value = true
  try {
    await configStore.save({
      ai: {
        model_id: modelId.value,
        timeout: aiTimeout.value,
        max_retries: maxRetries.value,
        comment: {
          enabled: commentEnabled.value,
          max_comments: maxComments.value,
          max_related: maxRelated.value,
          user_intent: userIntent.value,
          style: commentStyle.value,
          max_length: maxLength.value,
          min_length: minLength.value,
          enable_image: commentEnableImage.value,
          images: commentImagePath.value ? [commentImagePath.value] : [],
        },
        filter: {
          enabled: filterEnabled.value,
          criteria: criteria.value,
          sensitivity: sensitivity.value,
          use_comments: useComments.value,
          use_related: useRelated.value,
        },
      },
    }, slotStore.currentSlot)
    alertModal.success('AI 配置已保存')
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || String(e)
    alertModal.error('保存失败: ' + (Array.isArray(msg) ? msg.join(', ') : msg))
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  if (!modelId.value) {
    testStatus.value = '请先选择模型'
    return
  }
  testing.value = true
  testStatus.value = '测试中...'
  try {
    const { data } = await modelsApi.test(modelId.value)
    testStatus.value = data?.ok ? 'OK' : (data?.message || '失败')
  } catch (e) {
    testStatus.value = e?.response?.data?.message || e?.message || 'Error'
  } finally {
    testing.value = false
  }
}

async function browseCommentImage() {
  browsingImage.value = true
  try {
    const { data } = await fileApi.browseImage()
    if (data?.path) commentImagePath.value = data.path
  } catch { /* cancelled */ }
  browsingImage.value = false
}
</script>

<template>
  <div class="max-w-2xl space-y-5">
    <!-- API 连接：模型选择来自项目固定配置 -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">API 连接</h3>
      <p class="text-xs text-gray-500 mb-4">选择要启用的模型（API Key 等在项目模型配置中填写）。普通评论无需配置。</p>
      <div class="space-y-3">
        <div>
          <label class="text-xs text-gray-500">模型</label>
          <select v-model="modelId" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-transparent">
            <option v-for="m in modelList" :key="m.id" :value="m.id">{{ m.model_name }}{{ m.price ? ' — ' + m.price : '' }}</option>
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
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
      <div class="grid grid-cols-2 gap-3 mb-3">
        <div>
          <label class="text-xs text-gray-500">评论区热门评论获取量（条）</label>
          <input v-model.number="maxComments" type="number" min="1" max="30" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
        <div>
          <label class="text-xs text-gray-500">相关视频标题获取量（条）</label>
          <input v-model.number="maxRelated" type="number" min="1" max="20" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
      </div>
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
      <div class="mt-4">
        <label class="flex items-center gap-2 text-sm mb-2">
          <input type="checkbox" v-model="commentEnableImage" class="accent-blue-600" /> 启用图片
        </label>
        <div class="flex gap-2">
          <input
            v-model="commentImagePath"
            type="text"
            placeholder="图片路径（可选）"
            class="flex-1 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-transparent"
          />
          <button
            type="button"
            @click="browseCommentImage"
            :disabled="browsingImage"
            class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50"
          >
            {{ browsingImage ? '选择中...' : '选择图片' }}
          </button>
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
      <div class="mt-4 space-y-2">
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" v-model="useComments" class="accent-blue-600" /> 拉取评论区（供筛选/评论参考）
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" v-model="useRelated" class="accent-blue-600" /> 拉取推荐视频标题（供筛选/评论参考）
        </label>
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
