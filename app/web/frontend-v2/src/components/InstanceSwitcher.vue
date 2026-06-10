<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSlotStore } from '../stores/slot'
import { useTaskStore } from '../stores/task'
import { useAlertModalStore } from '../stores/alertModal'

const slotStore = useSlotStore()
const taskStore = useTaskStore()
const alertModal = useAlertModalStore()
const emit = defineEmits(['change'])

const isOpen = ref(false)
const dropdownRef = ref(null)

const slotsWithStatus = computed(() => {
  return slotStore.slots.map(slot => {
    const isCurrentSlot = slot.id === slotStore.currentSlot
    // 优先使用后端返回的 isRunning 状态
    // 如果后端没有返回（undefined），则对当前槽位使用前端状态
    const isRunning = slot.isRunning !== undefined
      ? slot.isRunning
      : (isCurrentSlot && taskStore.isAnyRunning)
    return {
      ...slot,
      isRunning,
      status: isRunning ? 'running' : 'idle',
      statusLabel: isRunning ? '运行中' : '空闲',
      canDelete: slot.id !== '0' && slot.id !== slotStore.currentSlot
    }
  })
})

const currentSlotInfo = computed(() => {
  return slotsWithStatus.value.find(s => s.id === slotStore.currentSlot) || slotsWithStatus.value[0]
})

function toggleDropdown() {
  if (!slotStore.switching) {
    isOpen.value = !isOpen.value
  }
}

function selectSlot(slotId) {
  if (slotId !== slotStore.currentSlot && !slotStore.switching) {
    emit('change', slotId)
    isOpen.value = false
  }
}

async function deleteSlot(slotId, event) {
  event.stopPropagation()

  if (slotId === '0') {
    alertModal.error('不能删除实例 0')
    return
  }

  if (slotId === slotStore.currentSlot) {
    alertModal.error('不能删除当前正在使用的实例')
    return
  }

  if (!confirm(`确定要删除实例 ${slotId} 吗？\n\n删除后该实例的所有配置和数据将被永久删除。`)) {
    return
  }

  try {
    await slotStore.deleteInstance(slotId)
  } catch (error) {
    alertModal.error(error.response?.data?.detail || error.message || '删除实例失败')
  }
}

function handleClickOutside(event) {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div ref="dropdownRef" class="relative">
    <button
      @click="toggleDropdown"
      :disabled="slotStore.switching"
      class="flex items-center gap-2 px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 focus:ring-1 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all min-w-[140px]"
    >
      <span class="flex-1 text-left">{{ currentSlotInfo.label }}</span>
      <span
        class="text-xs px-1.5 py-0.5 rounded-full flex-shrink-0"
        :class="currentSlotInfo.isRunning
          ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
          : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'"
      >
        {{ currentSlotInfo.statusLabel }}
      </span>
      <svg
        class="w-4 h-4 transition-transform flex-shrink-0"
        :class="{ 'rotate-180': isOpen }"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <Transition name="dropdown">
      <div
        v-if="isOpen"
        class="absolute right-0 mt-1 w-full min-w-[200px] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden z-50"
      >
        <div
          v-for="slot in slotsWithStatus"
          :key="slot.id"
          class="flex items-center justify-between px-3 py-2 text-xs transition-colors group"
          :class="slot.id === slotStore.currentSlot
            ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
            : 'hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'"
        >
          <div @click="selectSlot(slot.id)" class="flex items-center gap-2 flex-1 cursor-pointer">
            <span>{{ slot.label }}</span>
            <span
              class="text-xs px-1.5 py-0.5 rounded-full"
              :class="slot.isRunning
                ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'"
            >
              {{ slot.statusLabel }}
            </span>
          </div>
          <button
            v-if="slot.canDelete"
            @click="deleteSlot(slot.id, $event)"
            class="ml-2 p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
            title="删除实例"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
