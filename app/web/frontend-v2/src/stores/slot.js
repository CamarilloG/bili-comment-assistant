import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { instancesApi } from '../api'

export const useSlotStore = defineStore('slot', () => {
  const currentSlot = ref('0')
  const slots = ref([{ id: '0', label: '实例 0' }])

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

  async function addInstance() {
    try {
      const { data } = await instancesApi.add()
      if (data.slots && data.slots.length) {
        slots.value = data.slots
      }
      if (data.id) {
        currentSlot.value = data.id
      }
    } catch {
      // ignore error; 保持现有实例列表
    }
  }

  function setSlot(id) {
    currentSlot.value = id
  }

  return { currentSlot, slots, loadSlots, addInstance, setSlot }
})
