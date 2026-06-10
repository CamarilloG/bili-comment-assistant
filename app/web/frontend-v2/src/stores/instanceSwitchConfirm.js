import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useInstanceSwitchConfirmStore = defineStore('instanceSwitchConfirm', () => {
  const visible = ref(false)
  const targetSlot = ref(null)
  const currentSlot = ref(null)
  const resolveCallback = ref(null)

  function show(current, target) {
    currentSlot.value = current
    targetSlot.value = target
    visible.value = true

    return new Promise((resolve) => {
      resolveCallback.value = resolve
    })
  }

  function confirm() {
    visible.value = false
    if (resolveCallback.value) {
      resolveCallback.value(true)
      resolveCallback.value = null
    }
  }

  function cancel() {
    visible.value = false
    if (resolveCallback.value) {
      resolveCallback.value(false)
      resolveCallback.value = null
    }
  }

  return {
    visible,
    targetSlot,
    currentSlot,
    show,
    confirm,
    cancel
  }
})
