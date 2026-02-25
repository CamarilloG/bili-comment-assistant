import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAlertModalStore = defineStore('alertModal', () => {
  const visible = ref(false)
  const message = ref('')
  const type = ref('success') // 'success' | 'error'

  function show(msg, msgType = 'success') {
    message.value = msg
    type.value = msgType
    visible.value = true
  }

  function close() {
    visible.value = false
  }

  function success(msg) {
    show(msg, 'success')
  }

  function error(msg) {
    show(msg, 'error')
  }

  return { visible, message, type, show, close, success, error }
})
