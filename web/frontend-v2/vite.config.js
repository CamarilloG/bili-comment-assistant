import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  base: '/panel/',
  server: {
    proxy: {
      '/api': 'http://localhost:9527',
      '/ws': { target: 'ws://localhost:9527', ws: true },
    },
  },
})
