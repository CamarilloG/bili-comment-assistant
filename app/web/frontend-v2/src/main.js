import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

import Dashboard from './views/Dashboard.vue'
import CommentSettings from './views/CommentSettings.vue'
import AISettings from './views/AISettings.vue'
import WarmupPanel from './views/WarmupPanel.vue'
import BaseSettings from './views/BaseSettings.vue'

const routes = [
  { path: '/', component: Dashboard, meta: { title: '控制台' } },
  { path: '/comment', component: CommentSettings, meta: { title: '评论设置' } },
  { path: '/ai', component: AISettings, meta: { title: 'AI 设置' } },
  { path: '/warmup', component: WarmupPanel, meta: { title: '养号设置' } },
  { path: '/settings', component: BaseSettings, meta: { title: '基础设置' } },
]

const router = createRouter({
  history: createWebHistory('/panel/'),
  routes,
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
