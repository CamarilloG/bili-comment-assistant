# Bilibili Bot v3.7 Bug 修复说明

## 修复内容

### 1. 非前台实例状态显示错误 ✅

**问题描述：**
- 非当前实例的状态始终显示为"空闲"
- 即使后台实例正在运行任务，前端也不显示

**根本原因：**
- 前端 `InstanceSwitcher.vue` 只检查当前槽位的运行状态
- 后端已经返回每个实例的 `isRunning` 状态，但前端没有使用

**修复方案：**
1. 修改 `InstanceSwitcher.vue`：使用后端返回的 `isRunning` 状态
2. 添加 `slot.js` 状态轮询：每 3 秒刷新所有实例状态
3. 在 `App.vue` 中启动/停止状态轮询

**修改文件：**
- `app/web/frontend-v2/src/components/InstanceSwitcher.vue`
- `app/web/frontend-v2/src/stores/slot.js`
- `app/web/frontend-v2/src/App.vue`

---

### 2. 高级模型调用频率限制优化 ✅

**问题描述：**
- Gemini/GPT 等高级模型经常请求失败
- 推测是调用间隔太短导致频率限制
- Grok/OSS/Arcee 等模型很少出现问题

**根本原因：**
- 高级模型有更严格的频率限制
- 原有重试延迟固定为 `1.0 * attempt` 秒，不够灵活
- 没有请求间隔控制机制

**修复方案：**
1. 添加 `request_interval` 参数：控制两次请求之间的最小间隔
2. 添加 `retry_delay_base` 参数：可配置的重试延迟基数
3. 记录上次请求时间，自动等待到达间隔时间
4. 支持指数退避重试策略

**新增配置参数：**
```yaml
ai:
  # 调用间隔（秒）：两次 AI 请求之间的最小间隔
  # 高级模型（如 gemini/gpt）建议设置为 2-5 秒
  request_interval: 0

  # 重试延迟基数（秒）：重试延迟 = retry_delay_base * 重试次数
  # 例如：retry_delay_base=2，第1次重试延迟2秒，第2次延迟4秒
  retry_delay_base: 2.0
```

**修改文件：**
- `app/core/ai_provider.py`
- `app/core/ai_manager.py`
- `app/config.template.yaml`

---

## 使用建议

### 针对不同模型的配置建议：

**高级模型（Gemini/GPT/Claude）：**
```yaml
ai:
  timeout: 60
  max_retries: 3
  request_interval: 3.0      # 3秒间隔
  retry_delay_base: 3.0      # 重试延迟：3s, 6s, 9s
```

**中级模型（Grok/Qwen）：**
```yaml
ai:
  timeout: 30
  max_retries: 2
  request_interval: 1.0      # 1秒间隔
  retry_delay_base: 2.0      # 重试延迟：2s, 4s
```

**快速模型（DeepSeek/OSS）：**
```yaml
ai:
  timeout: 30
  max_retries: 2
  request_interval: 0        # 无间隔限制
  retry_delay_base: 2.0      # 重试延迟：2s, 4s
```

---

## 部署步骤

### 1. 重新构建前端
```bash
cd app/web/frontend-v2
npm run build
```

### 2. 更新配置文件
如果使用现有配置，需要手动添加新参数：
```yaml
ai:
  request_interval: 0
  retry_delay_base: 2.0
```

### 3. 重新打包（如需）
```bash
python -m PyInstaller launcher.spec --clean
```

或使用便携版打包：
```bash
build_portable.bat
```

---

## 测试验证

### 测试实例状态显示：
1. 启动多个实例
2. 在不同实例中启动任务
3. 切换实例，观察状态显示是否正确
4. 非当前实例运行时应显示"运行中"（绿色）

### 测试模型调用：
1. 配置高级模型（如 gemini）
2. 设置 `request_interval: 3.0`
3. 启动评论任务
4. 观察日志中的调用间隔和重试延迟
5. 应该看到 "调用间隔控制：等待 X.Xs" 的日志

---

## 版本信息
- 版本：v3.7
- 更新日期：2026-02-28
- 修复问题：实例状态显示 + 模型调用优化
