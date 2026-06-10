<script setup>
import { ref, onMounted, watch } from 'vue'
import { useConfigStore } from '../stores/config'
import { useSlotStore } from '../stores/slot'
import { useAlertModalStore } from '../stores/alertModal'

const configStore = useConfigStore()
const slotStore = useSlotStore()
const alertModal = useAlertModalStore()

// 百度机器人配置
const baiduEnabled = ref(false)
const baiduApiUrl = ref('http://apiin.im.baidu.com/api/msg/groupmsgsend')
const baiduAccessToken = ref('')
const baiduGroupId = ref('')

// 通知类型配置
const notifications = ref({
  captcha_alert: true,
  captcha_cooldown: true,
  captcha_terminated: true,
  cd_limit: true,
  comment_success: false,
  comment_failed: true,
  task_started: true,
  task_completed: true,
  task_error: true
})

const saving = ref(false)
const testing = ref(false)

onMounted(() => {
  if (configStore.config) loadFromConfig(configStore.config)
  watch(() => configStore.config, (c) => { if (c) loadFromConfig(c) })
})

function loadFromConfig(c) {
  const baidu = c.bots?.baidu || {}
  baiduEnabled.value = baidu.enabled || false
  baiduApiUrl.value = baidu.api_url || 'http://apiin.im.baidu.com/api/msg/groupmsgsend'
  baiduAccessToken.value = baidu.access_token || ''
  baiduGroupId.value = baidu.group_id || ''

  // 加载通知配置
  if (baidu.notifications) {
    notifications.value = { ...notifications.value, ...baidu.notifications }
  }
}

async function saveConfig() {
  saving.value = true
  try {
    await configStore.save({
      bots: {
        baidu: {
          enabled: baiduEnabled.value,
          api_url: baiduApiUrl.value,
          access_token: baiduAccessToken.value,
          group_id: baiduGroupId.value,
          notifications: notifications.value
        }
      }
    }, slotStore.currentSlot)
    alertModal.success('机器人配置已保存')
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || String(e)
    alertModal.error('保存失败: ' + (Array.isArray(msg) ? msg.join(', ') : msg))
  } finally {
    saving.value = false
  }
}

async function testNotification() {
  if (!baiduEnabled.value) {
    alertModal.error('请先启用百度机器人')
    return
  }

  if (!baiduAccessToken.value || !baiduGroupId.value) {
    alertModal.error('请填写完整的配置信息')
    return
  }

  testing.value = true
  try {
    // 调用后端 API 进行测试（完全按照 baidu_webhook_test.py 的方式）
    const response = await fetch(`/api/bot/baidu/test?slot=${slotStore.currentSlot}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })

    const result = await response.json()

    if (result.status === 'ok') {
      alertModal.success(result.message)
    } else {
      alertModal.error(result.message)
    }
  } catch (e) {
    alertModal.error('发送失败: ' + (e?.message || String(e)))
  } finally {
    testing.value = false
  }
}

// 通知类型配置项
const notificationTypes = [
  { key: 'captcha_alert', label: '验证码提醒', desc: '检测到验证码时立即通知', icon: '🚨', recommended: true },
  { key: 'captcha_cooldown', label: '验证码冷却', desc: '触发验证码后进入冷却期', icon: '⏸️', recommended: true },
  { key: 'captcha_terminated', label: '验证码达上限', desc: '验证码次数达到上限，任务终止', icon: '🛑', recommended: true },
  { key: 'cd_limit', label: 'CD 限制', desc: '触发 CD 限制，进入长时间养号', icon: '⏸️', recommended: true },
  { key: 'comment_success', label: '评论成功', desc: '每次评论成功时通知（可能很频繁）', icon: '✅', recommended: false },
  { key: 'comment_failed', label: '评论失败', desc: '评论失败时通知', icon: '❌', recommended: true },
  { key: 'task_started', label: '任务开始', desc: '任务启动时通知', icon: '▶️', recommended: true },
  { key: 'task_completed', label: '任务完成', desc: '任务完成时通知', icon: '✅', recommended: true },
  { key: 'task_error', label: '任务错误', desc: '任务出现错误时通知', icon: '⚠️', recommended: true }
]
</script>

<template>
  <div class="max-w-4xl space-y-5">
    <!-- 百度机器人配置 -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h3 class="text-sm font-semibold">百度内部通讯机器人</h3>
          <p class="text-xs text-gray-500 mt-1">接收任务状态、验证码提醒等通知</p>
        </div>
        <label class="relative inline-flex items-center cursor-pointer">
          <input type="checkbox" v-model="baiduEnabled" class="sr-only peer">
          <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
        </label>
      </div>

      <div v-if="baiduEnabled" class="space-y-3">
        <div>
          <label class="text-xs text-gray-500">API 地址</label>
          <input v-model="baiduApiUrl" placeholder="http://apiin.im.baidu.com/api/msg/groupmsgsend"
            class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-transparent" />
        </div>

        <div>
          <label class="text-xs text-gray-500">Access Token</label>
          <input v-model="baiduAccessToken" type="password" placeholder="请输入 Access Token"
            class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-transparent" />
          <p class="text-xs text-gray-400 mt-1">⚠️ 请妥善保管，不要泄露</p>
        </div>

        <div>
          <label class="text-xs text-gray-500">群组 ID</label>
          <input v-model="baiduGroupId" placeholder="请输入群组 ID"
            class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-transparent" />
        </div>

        <div class="flex gap-2 pt-2">
          <button @click="testNotification" :disabled="testing"
            class="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50">
            {{ testing ? '发送中...' : '🧪 发送测试消息' }}
          </button>
        </div>
      </div>
    </section>

    <!-- 通知类型配置 -->
    <section v-if="baiduEnabled" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">消息通知类型</h3>
      <p class="text-xs text-gray-500 mb-4">选择需要接收的通知类型</p>

      <div class="space-y-3">
        <div v-for="type in notificationTypes" :key="type.key"
          class="flex items-start gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
          <label class="relative inline-flex items-center cursor-pointer mt-0.5">
            <input type="checkbox" v-model="notifications[type.key]" class="sr-only peer">
            <div class="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
          </label>

          <div class="flex-1">
            <div class="flex items-center gap-2">
              <span class="text-lg">{{ type.icon }}</span>
              <span class="text-sm font-medium">{{ type.label }}</span>
              <span v-if="type.recommended" class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300">推荐</span>
            </div>
            <p class="text-xs text-gray-500 mt-1">{{ type.desc }}</p>
          </div>
        </div>
      </div>

      <div class="mt-4 p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
        <p class="text-xs text-yellow-800 dark:text-yellow-200">
          💡 提示：建议关闭"评论成功"通知，避免消息过于频繁。其他通知类型建议保持开启，以便及时了解任务状态。
        </p>
      </div>
    </section>

    <!-- 保存按钮 -->
    <div class="flex justify-end">
      <button @click="saveConfig" :disabled="saving"
        class="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
        {{ saving ? '保存中...' : '保存配置' }}
      </button>
    </div>
  </div>
</template>
