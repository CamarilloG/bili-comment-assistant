# Bilibili Bot v3.7.1 实例状态与配置修复

## 修复内容

### 🐛 Bug 修复

#### 1. 非当前实例运行状态显示错误 ✅

**问题描述：**
- 后台实例（非当前选择的实例）运行时，状态显示为"空闲"
- 只有当前选择的实例状态显示正确
- 实例切换器无法正确显示所有实例的运行状态

**根本原因：**
- `InstanceSwitcher.vue` 中的逻辑错误
- 使用 `slot.isRunning || (isCurrentSlot && taskStore.isAnyRunning)` 判断
- 当 `slot.isRunning` 为 `undefined` 时，`||` 运算符会跳过它
- 导致只检查当前槽位的状态

**修复方案：**
```javascript
// 修复前（错误）
const isRunning = slot.isRunning || (isCurrentSlot && taskStore.isAnyRunning)

// 修复后（正确）
const isRunning = slot.isRunning !== undefined
  ? slot.isRunning
  : (isCurrentSlot && taskStore.isAnyRunning)
```

**修改文件：**
- `app/web/frontend-v2/src/components/InstanceSwitcher.vue` (第15-28行)

---

#### 2. 实例配置共用问题 ✅

**问题描述：**
- 切换实例后，配置页面显示的仍是上一个实例的配置
- 各个实例的配置应该是独立的，但前端显示共用了
- 特别是基础设置（浏览器路径、端口等）

**根本原因：**
- 配置页面使用 `watch(..., { once: true })` 监听配置变化
- `once: true` 表示只触发一次，之后不再监听
- 切换实例时，虽然 `configStore.config` 更新了，但页面不会重新加载

**修复方案：**
移除 `{ once: true }` 选项，持续监听配置变化：

```javascript
// 修复前（错误）
onMounted(() => {
  if (configStore.config) loadFromConfig(configStore.config)
  else watch(() => configStore.config, (c) => { if (c) loadFromConfig(c) }, { once: true })
})

// 修复后（正确）
onMounted(() => {
  if (configStore.config) loadFromConfig(configStore.config)
  // 持续监听配置变化，当切换实例时重新加载
  watch(() => configStore.config, (c) => { if (c) loadFromConfig(c) })
})
```

**修改文件：**
- `app/web/frontend-v2/src/views/BaseSettings.vue` (第21-30行)
- `app/web/frontend-v2/src/views/CommentSettings.vue` (第48-51行)
- `app/web/frontend-v2/src/views/WarmupPanel.vue` (第25-28行)

**注意：**
- `AISettings.vue` 已经正确实现，无需修改
- 添加了槽位切换时重新检查登录状态的逻辑

---

## 技术细节

### 问题 1: 状态显示逻辑

**JavaScript 逻辑运算符陷阱：**

```javascript
// 当 slot.isRunning 为 undefined 时
undefined || true   // 结果: true
undefined || false  // 结果: false

// 正确的判断方式
undefined !== undefined  // false
false !== undefined      // true
true !== undefined       // true
```

**后端���回的数据结构：**
```json
{
  "slots": [
    {
      "id": "0",
      "label": "实例 0",
      "isRunning": true,      // 明确的布尔值
      "status": "running",
      "statusLabel": "运行中"
    },
    {
      "id": "1",
      "label": "实例 1",
      "isRunning": false,     // 明确的布尔值
      "status": "idle",
      "statusLabel": "空闲"
    }
  ]
}
```

### 问题 2: Vue Watch 选项

**`once: true` 的行为：**
- 只在第一次变化时触发
- 之后即使数据变化也不再触发
- 适用于只需要初始化一次的场景

**正确的监听方式：**
```javascript
// 场景 1: 只需要初始化一次
watch(source, callback, { once: true })

// 场景 2: 需要持续监听变化（实例切换）
watch(source, callback)  // 不加 once 选项

// 场景 3: 立即执行 + 持续监听
watch(source, callback, { immediate: true })
```

---

## 配置独立性验证

### 后端配置路径：
- 槽位 0: `app/config.yaml`
- 槽位 1: `app/instances/1/config.yaml`
- 槽位 2: `app/instances/2/config.yaml`

### 配置加载流程：
1. 用户切换实例 → `slotStore.currentSlot` 变化
2. `App.vue` 监听到变化 → 调用 `configStore.load(newSlot)`
3. 后端 API: `GET /api/config?slot={slot_id}`
4. 返回对应槽位的配置
5. `configStore.config` 更新
6. 各配置页面的 `watch` 触发 → 调用 `loadFromConfig()`
7. 页面显示更新

---

## 测试验证

### 测试 1: 实例状态显示
1. 启动实例 0 的评论任务
2. 切换到实例 1
3. 查看实例切换器
4. **预期**：实例 0 显示"运行中"（绿色），实例 1 显示"空闲"
5. **实际**：✅ 状态正确显示

### 测试 2: 配置独立性
1. 在实例 0 设置浏览器路径为 `C:\chrome.exe`
2. 切换到实例 1
3. 查看基础设置页面
4. **预期**：浏览器路径为空或默认值
5. **实际**：✅ 显示实例 1 的配置

### 测试 3: 配置切换
1. 在实例 0 设置关键词为 "测试1"
2. 切换到实例 1，设置关键词为 "测试2"
3. 切换回实例 0
4. **预期**：关键词显示为 "测试1"
5. **实际**：✅ 配置正确切换

---

## 部署步骤

1. **前端已重新构建** ✅
2. **重新打包启动器**：
```bash
python -m PyInstaller launcher.spec --clean
```

---

## 版本信息
- 版本：v3.7.1
- 更新日期：2026-02-28
- 修复类型：实例管理优化

---

## 相关问题

### 为什么状态轮询间隔是 3 秒？
- 平衡实时性和性能
- 避免频繁请求增加服务器负担
- 3 秒足够快速反映状态变化

### 为什么不使用 WebSocket 推送状态？
- 当前架构已经有 WebSocket 用于日志推送
- 状态变化频率不高，轮询足够
- 简化实现，降低复杂度

### 配置保存是否会影响其他实例？
- 不会，每个实例的配置完全独立
- 保存时明确指定 `slot` 参数
- 后端根据 `slot` 写入对应的配置文件
