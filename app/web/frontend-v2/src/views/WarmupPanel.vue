<script setup>
import { ref, onMounted, watch } from 'vue'
import { useConfigStore } from '../stores/config'
import { useSlotStore } from '../stores/slot'
import { useAlertModalStore } from '../stores/alertModal'

const configStore = useConfigStore()
const slotStore = useSlotStore()
const alertModal = useAlertModalStore()

const durationMinutes = ref(30)
const maxVideos = ref(50)
const watchTimeMin = ref(20)
const watchTimeMax = ref(240)
const randomPause = ref(true)
const randomScroll = ref(true)
const viewComment = ref(true)
const randomLike = ref(true)
const likeProbability = ref(0.3)
const commentEnable = ref(false)
const commentProbability = ref(0.1)
const source = ref('recommend')
const saving = ref(false)

onMounted(() => {
  if (configStore.config?.warmup) loadFromConfig(configStore.config.warmup)
  // 监听配置变化，当切换实例时重新加载
  watch(() => configStore.config?.warmup, (w) => { if (w) loadFromConfig(w) })
})

function loadFromConfig(w) {
  durationMinutes.value = w.basic?.duration_minutes || 30
  maxVideos.value = w.basic?.max_videos || 50
  watchTimeMin.value = w.behavior?.watch_time_min || 20
  watchTimeMax.value = w.behavior?.watch_time_max || 240
  randomPause.value = w.behavior?.random_pause ?? true
  randomScroll.value = w.behavior?.random_scroll ?? true
  viewComment.value = w.behavior?.view_comment ?? true
  randomLike.value = w.behavior?.random_like ?? true
  likeProbability.value = w.behavior?.like_prob || 0.3
  commentEnable.value = w.comment?.enable || false
  commentProbability.value = w.comment?.probability || 0.1
  source.value = w.source || 'recommend'
}

async function saveConfig() {
  saving.value = true
  try {
    await configStore.save({
      warmup: {
        basic: { duration_minutes: Number(durationMinutes.value), max_videos: Number(maxVideos.value) },
        behavior: {
          watch_time_min: Number(watchTimeMin.value),
          watch_time_max: Number(watchTimeMax.value),
          random_pause: randomPause.value,
          pause_prob: 0.005,
          random_scroll: randomScroll.value,
          scroll_prob: 0.01,
          view_comment: viewComment.value,
          view_comment_prob: 0.005,
          random_like: randomLike.value,
          like_prob: Number(likeProbability.value),
        },
        comment: {
          enable: commentEnable.value,
          probability: Number(commentProbability.value),
          type: 'template',
        },
        source: source.value,
      },
    }, slotStore.currentSlot)
    alertModal.success('养号设置已保存')
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || String(e)
    alertModal.error('保存失败: ' + (Array.isArray(msg) ? msg.join(', ') : msg))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl space-y-5">
    <!-- Basic -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">基本设置</h3>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="text-xs text-gray-500">养号时长(分钟)</label>
          <input v-model.number="durationMinutes" type="number" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
        <div>
          <label class="text-xs text-gray-500">最大视频数</label>
          <input v-model.number="maxVideos" type="number" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
        <div>
          <label class="text-xs text-gray-500">视频来源</label>
          <select v-model="source" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent">
            <option value="recommend">推荐页</option>
            <option value="hot">热门</option>
          </select>
        </div>
      </div>
    </section>

    <!-- Watch Behavior -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">观看行为</h3>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="text-xs text-gray-500">最短观看(s)</label>
          <input v-model.number="watchTimeMin" type="number" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
        <div>
          <label class="text-xs text-gray-500">最长观看(s)</label>
          <input v-model.number="watchTimeMax" type="number" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
      </div>
      <div class="flex flex-wrap gap-4 mt-4">
        <label class="flex items-center gap-1.5 text-sm"><input type="checkbox" v-model="randomPause" class="accent-blue-600" /> 随机暂停</label>
        <label class="flex items-center gap-1.5 text-sm"><input type="checkbox" v-model="randomScroll" class="accent-blue-600" /> 随机滚动</label>
        <label class="flex items-center gap-1.5 text-sm"><input type="checkbox" v-model="viewComment" class="accent-blue-600" /> 浏览评论</label>
        <label class="flex items-center gap-1.5 text-sm"><input type="checkbox" v-model="randomLike" class="accent-blue-600" /> 随机点赞</label>
      </div>
      <div class="mt-3">
        <label class="text-xs text-gray-500">点赞概率</label>
        <input v-model.number="likeProbability" type="number" step="0.05" min="0" max="1" class="w-32 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
      </div>
    </section>

    <!-- Comment -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">评论行为</h3>
      <div class="flex items-center gap-4">
        <label class="flex items-center gap-1.5 text-sm"><input type="checkbox" v-model="commentEnable" class="accent-blue-600" /> 启用评论</label>
        <div>
          <label class="text-xs text-gray-500 mr-1">评论概率</label>
          <input v-model.number="commentProbability" type="number" step="0.05" min="0" max="1" class="w-24 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
      </div>
    </section>

    <!-- Save -->
    <button
      @click="saveConfig"
      :disabled="saving"
      class="w-full py-2.5 rounded-xl text-sm font-medium text-white bg-orange-500 hover:bg-orange-600 disabled:opacity-50 transition-colors"
    >
      {{ saving ? '保存中...' : '保存养号配置' }}
    </button>
  </div>
</template>
