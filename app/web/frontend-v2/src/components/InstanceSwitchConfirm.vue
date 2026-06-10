<script setup>
import { useInstanceSwitchConfirmStore } from '../stores/instanceSwitchConfirm'

const confirmStore = useInstanceSwitchConfirmStore()
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="confirmStore.visible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="confirmStore.cancel"
      >
        <div class="bg-white dark:bg-gray-900 rounded-xl border-2 border-yellow-500 shadow-xl max-w-md w-full mx-4 p-6">
          <div class="flex items-start gap-3 mb-4">
            <svg class="w-6 h-6 text-yellow-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div class="flex-1">
              <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                确认切换实例
              </h3>
              <p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
                当前实例 <span class="font-semibold text-gray-900 dark:text-gray-100">{{ confirmStore.currentSlot }}</span> 有任务正在运行。
              </p>
              <p class="text-sm text-gray-600 dark:text-gray-400">
                切换到实例 <span class="font-semibold text-gray-900 dark:text-gray-100">{{ confirmStore.targetSlot }}</span> 将停止当前任务。是否继续？
              </p>
            </div>
          </div>

          <div class="flex gap-3 justify-end">
            <button
              @click="confirmStore.cancel"
              class="px-4 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            >
              取消
            </button>
            <button
              @click="confirmStore.confirm"
              class="px-4 py-2 rounded-lg text-sm font-medium text-white bg-yellow-600 hover:bg-yellow-700 transition-colors"
            >
              强制切换
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
  transition: opacity 0.2s;
}

.modal-enter-active > div,
.modal-leave-active > div {
  transition: transform 0.2s, opacity 0.2s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from > div,
.modal-leave-to > div {
  transform: scale(0.95);
  opacity: 0;
}
</style>
