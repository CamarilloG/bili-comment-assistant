<script setup>
import { ref, onMounted, watch } from 'vue'
import { useConfigStore } from '../stores/config'
import { authApi, fileApi } from '../api'

const configStore = useConfigStore()

const browserPath = ref('')
const browserPort = ref(0)
const headless = ref(false)

const loginStatus = ref(null)
const loginChecking = ref(false)
const browsingExe = ref(false)
const saving = ref(false)

onMounted(() => {
  if (configStore.config) loadFromConfig(configStore.config)
  else watch(() => configStore.config, (c) => { if (c) loadFromConfig(c) }, { once: true })
  checkAuth()
})

function loadFromConfig(c) {
  browserPath.value = c.browser?.path || ''
  browserPort.value = c.browser?.port || 0
  headless.value = c.behavior?.headless || false
}

async function saveConfig() {
  saving.value = true
  try {
    await configStore.save({
      browser: { path: browserPath.value, port: Number(browserPort.value) },
      behavior: { headless: headless.value },
    })
  } finally {
    saving.value = false
  }
}

async function browseExe() {
  browsingExe.value = true
  try {
    const { data } = await fileApi.browseExecutable()
    if (data.path) browserPath.value = data.path
  } catch { /* cancelled */ }
  browsingExe.value = false
}

async function checkAuth() {
  loginChecking.value = true
  try {
    const { data } = await authApi.status()
    loginStatus.value = data.logged_in
  } catch { loginStatus.value = null }
  loginChecking.value = false
}

async function doCheckLogin() {
  loginChecking.value = true
  await authApi.check()
  setTimeout(async () => {
    const { data } = await authApi.status()
    loginStatus.value = data.logged_in
    loginChecking.value = false
  }, 8000)
}

async function doQrLogin() {
  await authApi.startQrLogin()
}
</script>

<template>
  <div class="max-w-2xl space-y-5">
    <!-- Browser -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">浏览器设置</h3>
      <label class="text-xs text-gray-500">浏览器路径</label>
      <div class="flex gap-2 mb-3">
        <input v-model="browserPath" placeholder="chrome.exe 路径" class="flex-1 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm bg-transparent" />
        <button @click="browseExe" :disabled="browsingExe"
          class="shrink-0 px-3 py-2 text-xs rounded-lg border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50">
          {{ browsingExe ? '...' : '选择' }}
        </button>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="text-xs text-gray-500">调试端口</label>
          <input v-model.number="browserPort" type="number" class="w-full border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-transparent" />
        </div>
      </div>
      <label class="flex items-center gap-1.5 text-sm mt-3">
        <input type="checkbox" v-model="headless" class="accent-blue-600" /> 无头模式（不显示浏览器窗口）
      </label>
    </section>

    <!-- Login -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <h3 class="text-sm font-semibold mb-4">账号与登录</h3>
      <div class="flex items-center gap-3">
        <span
          class="text-sm px-3 py-1 rounded-full font-medium"
          :class="loginStatus === true ? 'bg-green-100 text-green-700' : loginStatus === false ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'"
        >
          {{ loginStatus === true ? '已登录' : loginStatus === false ? '未登录' : '未检测' }}
        </span>
        <button @click="doCheckLogin" :disabled="loginChecking"
          class="text-sm px-4 py-1.5 rounded-lg border border-gray-300 hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800 disabled:opacity-50">
          {{ loginChecking ? '检测中...' : '检测登录状态' }}
        </button>
        <button @click="doQrLogin"
          class="text-sm px-4 py-1.5 rounded-lg border border-blue-500 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30">
          扫码登录
        </button>
      </div>
      <p class="text-xs text-gray-400 mt-2">扫码登录会在服务端弹出浏览器窗口，请在弹出的页面中扫码。</p>
    </section>

    <!-- Placeholder -->
    <section class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 border-dashed p-5">
      <div class="text-center py-6">
        <p class="text-sm text-gray-400">更多设置即将到来</p>
        <p class="text-xs text-gray-300 mt-1">通知渠道、机器人接入等</p>
      </div>
    </section>

    <!-- Save -->
    <button
      @click="saveConfig"
      :disabled="saving"
      class="w-full py-2.5 rounded-xl text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 transition-colors"
    >
      {{ saving ? '保存中...' : '保存基础配置' }}
    </button>
  </div>
</template>
