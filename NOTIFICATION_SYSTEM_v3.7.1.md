# Bilibili Bot v3.7.1 全局通知系统实现

## 功能概述

实现了全局通知系统，支持：
1. **Web 端吐司通知**：任意实例检测到验证码时，前端显示吐司提示
2. **Windows 系统通知**：仅重要事件（验证码 + 连续失败 + 任务终止）触发系统通知
3. **连续失败追踪**：单一实例连续 3 次失败时发送通知

---

## 架构设计

### 后端架构

```
NotificationManager (核心管理器)
    ├── Web 通知回调系统
    ├── WebSocket 广播
    └── Windows 系统通知

WebSocket 端点: /ws/notifications
    └── 广播所有实例的通知到前端
```

### 前端架构

```
ToastNotification.vue (吐司组件)
    ├── WebSocket 连接
    ├── 自动重连机制
    └── 通知队列管理
```

---

## 实现细节

### 1. 后端通知管理器

**文件：`app/core/notification_manager.py`**

核心功能：
- 管理 Web 端通知回调
- 追踪每个实例的连续失败次数
- 发送 Windows 系统通知（仅重要事件）

```python
class NotificationManager:
    def notify_captcha(self, slot_id: str, count: int, cooldown_minutes: int):
        """验证码通知 - 必须显示系统通知"""

    def notify_failure(self, slot_id: str, reason: str):
        """记录失败，连续 3 次失败时发送通知"""

    def notify_terminated(self, slot_id: str, reason: str):
        """任务终止通知 - 必须显示系统通知"""

    def reset_failure_count(self, slot_id: str):
        """重置失败计数（成功时调用）"""
```

**通知类型：**
- `info`: 普通信息（蓝色）
- `warning`: 警告（黄色）
- `error`: 错误（红色）
- `captcha`: 验证码（橙色）- 必须显示系统通知
- `critical`: 严重错误（红色）- 必须显示系统通知

---

### 2. WebSocket 通知端点

**文件：`app/web/routers/notification_api.py`**

```python
@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket):
    """全局通知 WebSocket 端点"""
```

**特点：**
- 所有实例的通知都会推送给所有订阅者
- 自动重连机制
- 队列满时自动清理死连接

---

### 3. 前端吐司组件

**文件：`app/web/frontend-v2/src/components/ToastNotification.vue`**

**功能：**
- WebSocket 连接 `/ws/notifications`
- 自动重连（3 秒间隔）
- 通知自动消失：
  - 普通通知：5 秒
  - 验证码/严重错误：10 秒
- 手动关闭按钮
- 平滑动画效果

**通知样式：**
- 固定在右上角
- 最大宽度 `max-w-sm`
- 带图标和关闭按钮
- 根据类型显示不同颜色

---

### 4. 集成到主流程

**文件：`app/main.py`**

**验证码检测时：**
```python
if result == "captcha":
    # 发送全局通知
    notification_mgr.notify_captcha(slot_id, captcha_count, cooldown_minutes)
```

**评论成功时：**
```python
if result == "success":
    # 重置失败计数
    notification_mgr.reset_failure_count(slot_id)
```

**评论失败时：**
```python
else:
    # 记录失败（连续3次失败会自动发送通知）
    notification_mgr.notify_failure(slot_id, toast_message or "评论失败")
```

**任务终止时：**
```python
if captcha_count >= captcha_max_count:
    notification_mgr.notify_terminated(slot_id, f"今日验证码触发已达上限（{captcha_count}/{captcha_max_count}）")
```

---

## Windows 系统通知

### 支持的库

1. **plyer**（推荐）
   - 跨平台通知库
   - 支持 Windows 10/11
   - 安装：`pip install plyer`

2. **win10toast**（备选）
   - Windows 专用
   - 仅在 plyer 不可用时使用
   - 安装：`pip install win10toast`

### 通知触发条件

**必须显示系统通知的事件：**
1. 检测到验证码
2. 连续 3 次失败
3. 任务终止

**不显示系统通知的事件：**
- 单次评论失败
- 普通信息提示
- 配置更新

---

## 通知数据格式

### WebSocket 消息格式

```json
{
  "title": "实例 0 检测到验证码",
  "message": "今日第 1 次触发，将冷却 30 分钟",
  "type": "captcha",
  "slot_id": "0",
  "timestamp": 1709107200.123
}
```

### 字段说明

- `title`: 通知标题
- `message`: 通知内容
- `type`: 通知类型（info/warning/error/captcha/critical）
- `slot_id`: 实例 ID
- `timestamp`: Unix 时间戳

---

## 测试验证

### 测试 1: 验证码通知

1. 启动实例 0 的评论任务
2. 触发验证码
3. **预期**：
   - 前端显示橙色吐司通知："实例 0 检测到验证码"
   - Windows 系统通知弹出
   - 通知持续 10 秒后自动消失

### 测试 2: 连续失败通知

1. 启动实例 1 的评论任务
2. 连续失败 3 次
3. **预期**：
   - 前端显示红色吐司通知："实例 1 连续失败"
   - Windows 系统通知弹出
   - 显示失败次数和原因

### 测试 3: 多实例通知

1. 实例 0 和实例 1 同时运行
2. 实例 0 触发验证码
3. **预期**：
   - 所有打开的前端页面都显示通知
   - 通知明确标注"实例 0"

### 测试 4: 自动重连

1. 打开前端页面
2. 重启后端服务
3. **预期**：
   - WebSocket 自动重连
   - 控制台显示"reconnecting in 3s..."
   - 重连成功后继续接收通知

---

## 部署步骤

### 1. 安装依赖

```bash
pip install plyer
# 或
pip install win10toast
```

### 2. 重新构建前端

```bash
cd app/web/frontend-v2
npm run build
```

### 3. 重新打包启动器

```bash
python -m PyInstaller launcher.spec --clean
```

---

## 配置选项

### 失败计数阈值

在 `notification_manager.py` 中修改：

```python
if count >= 3:  # 修改这里的数字
    # 发送通知
```

### 通知持续时间

在 `ToastNotification.vue` 中修改：

```javascript
const duration = data.type === 'captcha' || data.type === 'critical' ? 10000 : 5000
// 修改这里的毫秒数
```

### 系统通知开关

在 `notification_manager.py` 中修改 `show_system` 参数：

```python
self.send_notification(
    title=title,
    message=message,
    notification_type="captcha",
    slot_id=slot_id,
    show_system=True,  # 改为 False 禁用系统通知
)
```

---

## 技术细节

### WebSocket 连接管理

**自动重连机制：**
```javascript
ws.onclose = () => {
  console.log('[Toast] WebSocket closed, reconnecting in 3s...')
  setTimeout(connectWebSocket, 3000)
}
```

**心跳检测：**
- 当前未实现心跳
- 依赖浏览器的 WebSocket 自动检测
- 如需添加心跳，可在 `ws.onopen` 后启动定时器

### 通知队列管理

**队列大小限制：**
```python
q: queue.Queue = queue.Queue(maxsize=128)
```

**满队列处理：**
- 队列满时，新通知会被丢弃
- 死连接会被自动清理

### 失败计数追踪

**数据结构：**
```python
self._failure_counts = {}  # slot_id -> count
```

**重置时机：**
- 评论成功时重置
- 不会自动过期（除非重启服务）

---

## 已知限制

1. **系统通知依赖外部库**
   - 需要安装 plyer 或 win10toast
   - 如果都不可用，系统通知会静默失败

2. **WebSocket 重连延迟**
   - 重连间隔固定为 3 秒
   - 可能导致短暂的通知丢失

3. **失败计数不持久化**
   - 重启服务后失败计数清零
   - 如需持久化，可使用数据库或文件

4. **通知不去重**
   - 相同通知可能重复显示
   - 如需去重，可在前端添加逻辑

---

## 未来优化方向

### 可能的改进：

1. **通知历史记录**
   - 保存最近 100 条通知
   - 提供查看历史的界面

2. **通知过滤**
   - 允许用户选择接收哪些类型的通知
   - 静音特定实例的通知

3. **声音提示**
   - 重要通知播放提示音
   - 可配置音量和音效

4. **邮件/微信推送**
   - 集成 Server 酱、PushPlus
   - 支持远程通知

5. **通知统计**
   - 统计每个实例的通知数量
   - 生成通知报告

---

## 版本信息

- 版本：v3.7.1
- 更新日期：2026-02-28
- 功能类型：全局通知系统

---

## 相关文件

### 后端文件：
- `app/core/notification_manager.py` - 通知管理器
- `app/web/routers/notification_api.py` - WebSocket 端点
- `app/main.py` - 集成通知调用

### 前端文件：
- `app/web/frontend-v2/src/components/ToastNotification.vue` - 吐司组件
- `app/web/frontend-v2/src/App.vue` - 集成吐司组件

### 配置文件：
- `app/web/app.py` - 注册通知路由
