import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { instancesApi } from '../api'

const MAX_INSTANCES = 10

export const useSlotStore = defineStore('slot', () => {
  const currentSlot = ref('0')
  const slots = ref([{ id: '0', label: '实例 0' }])
  const switching = ref(false)
  const switchError = ref(null)
  let statusPollingTimer = null

  const canAddInstance = computed(() => {
    // 槽位 0 不计入上限
    const nonZeroSlots = slots.value.filter(s => s.id !== '0')
    return nonZeroSlots.length < MAX_INSTANCES
  })

  async function loadSlots() {
    try {
      const { data } = await instancesApi.get()
      if (data.slots && data.slots.length) {
        slots.value = data.slots
      }
    } catch {
      slots.value = [{ id: '0', label: '实例 0' }]
    }
  }

  // 启动定期刷新所有实例状态
  function startStatusPolling() {
    stopStatusPolling()
    statusPollingTimer = setInterval(() => {
      loadSlots() // 每 3 秒刷新一次所有实例状态
    }, 3000)
  }

  // 停止状态轮询
  function stopStatusPolling() {
    if (statusPollingTimer) {
      clearInterval(statusPollingTimer)
      statusPollingTimer = null
    }
  }

  async function addInstance() {
    if (!canAddInstance.value) {
      throw new Error(`最多只能创建 ${MAX_INSTANCES} 个实例`)
    }

    try {
      const { data } = await instancesApi.add()
      if (data.slots && data.slots.length) {
        slots.value = data.slots
      }
      if (data.id) {
        currentSlot.value = data.id
      }
    } catch (error) {
      throw error
    }
  }

  async function deleteInstance(slotId) {
    if (slotId === '0') {
      throw new Error('不能删除实例 0')
    }

    if (slotId === currentSlot.value) {
      throw new Error('不能删除当前正在使用的实例')
    }

    try {
      const { data } = await instancesApi.delete(slotId)
      if (data.slots && data.slots.length) {
        slots.value = data.slots
      }
    } catch (error) {
      throw error
    }
  }

  async function setSlot(id, force = false) {
    if (switching.value) {
      throw new Error('正在切换实例，请稍候')
    }

    if (id === currentSlot.value) {
      return
    }

    try {
      switching.value = true
      switchError.value = null
      currentSlot.value = id
    } catch (error) {
      switchError.value = error.message || '切换失败'
      throw error
    } finally {
      switching.value = false
    }
  }

  function getSlotsWithStatus(taskStore) {
    // 后端已经返回了每个实例的运行状态，直接使用
    return slots.value
  }

  return {
    currentSlot,
    slots,
    switching,
    switchError,
    canAddInstance,
    loadSlots,
    addInstance,
    deleteInstance,
    setSlot,
    getSlotsWithStatus,
    startStatusPolling,
    stopStatusPolling
  }
})
