<script setup>
import { useAlertModalStore } from '../stores/alertModal'
import { storeToRefs } from 'pinia'

const alertModal = useAlertModalStore()
const { visible, message, type } = storeToRefs(alertModal)
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="visible"
        class="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/50"
        @click.self="alertModal.close()"
      >
        <div
          class="w-full max-w-md rounded-xl shadow-xl border p-5 bg-white dark:bg-gray-900"
          :class="type === 'error'
            ? 'border-red-200 dark:border-red-800'
            : 'border-gray-200 dark:border-gray-700'"
        >
          <p class="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{{ message }}</p>
          <div class="mt-4 flex justify-end">
            <button
              type="button"
              @click="alertModal.close()"
              class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              :class="type === 'error'
                ? 'bg-red-500 hover:bg-red-600 text-white'
                : 'bg-blue-600 hover:bg-blue-700 text-white'"
            >
              确定
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-active .rounded-xl,
.modal-leave-active .rounded-xl {
  transition: transform 0.2s ease;
}
.modal-enter-from .rounded-xl,
.modal-leave-to .rounded-xl {
  transform: scale(0.95);
}
</style>
