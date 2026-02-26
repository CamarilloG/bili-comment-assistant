import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useSlotStore = defineStore('slot', () => {
  const currentSlot = ref('0')
  const slots = ref([{ id: '0', label: '实例 0' }])

  async function loadSlots() {
    try {
      const { data } = await api.get('/instances')
      if (data.slots && data.slots.length) {
        slots.value = data.slots
      }
    } catch {
      slots.value = [{ id: '0', label: '实例 0' }]
    }
  }

  function setSlot(id) {
    currentSlot.value = id
  }

  return { currentSlot, slots, loadSlots, setSlot }
})
