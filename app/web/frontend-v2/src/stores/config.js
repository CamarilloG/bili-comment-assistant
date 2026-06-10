import { defineStore } from 'pinia'
import { ref } from 'vue'
import { configApi } from '../api'

export const useConfigStore = defineStore('config', () => {
  const config = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function load(slot = '0') {
    loading.value = true
    error.value = null
    try {
      const { data } = await configApi.get(slot)
      config.value = data
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function save(newConfig, slot = '0') {
    loading.value = true
    error.value = null
    try {
      const { data } = await configApi.update(newConfig, slot)
      config.value = { ...config.value, ...newConfig }
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return { config, loading, error, load, save }
})
