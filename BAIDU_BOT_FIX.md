# 百度机器人通知修复总结

**修复日期**: 2026-03-04
**问题**: 测试消息成功推送，但正式评论时没有按照配置推送消息

---

## 问题分析

### 根本原因

1. **配置加载问题**: `ConfigValidator.validate_and_fill_defaults()` 没有保留 `bots` 配置段
2. **初始化问题**: `NotificationManager` 创建后没有传入配置，导致百度机器人未初始化
3. **通知方法缺失**: `NotificationManager` 缺少部分通知方法

---

## 修复内容

### 1. 配置加载修复 ✅

**文件**: `app/core/config.py`

**问题**: `validate_and_fill_defaults()` 方法会丢弃 `bots` 配置

**修复**:
```python
# Line 200-202
if "warmup" in config:
    validated["warmup"] = config["warmup"]

# 保留 bots 配置（机器人通知）
if "bots" in config:
    validated["bots"] = config["bots"]

if strict:
    ConfigValidator._validate_required_fields(validated)
```

**验证**:
```bash
python -c "from core.config import ConfigValidator; from core.slot import get_config_path; \
config = ConfigValidator.load_config(get_config_path('0')); \
print('Baidu enabled:', config.get('bots', {}).get('baidu', {}).get('enabled'))"
# 输出: Baidu enabled: True
```

---

### 2. 通知管理器初始化修复 ✅

**文件**: `app/main.py`

**问题**: `notification_mgr` 创建后没有传入配置

**修复**:
```python
# Line 322-324
notification_mgr = get_notification_manager()
# 更新通知管理器配置（初始化百度机器人等）
notification_mgr.update_config(config)
ai_manager = AIManager(config)
```

**说明**:
- `get_notification_manager()` 返回全局单例
- 必须调用 `update_config(config)` 来初始化百度机器人
- 每次任务开始时都会更新配置，确保使用最新配置

---

### 3. 添加缺失的通知方法 ✅

**文件**: `app/core/notification_manager.py`

**新增方法**:

#### 3.1 评论成功通知
```python
def notify_comment_success(self, slot_id: str, video_title: str, comment_text: str):
    """评论成功通知"""
    if self._baidu_bot:
        try:
            self._baidu_bot.notify_comment_success(
                video_title=video_title,
                comment_text=comment_text,
                slot_id=int(slot_id)
            )
        except Exception as e:
            logger.error(f"[通知管理器] 百度机器人通知失败: {e}")
```

#### 3.2 单次评论失败通知
```python
def notify_comment_failed(self, slot_id: str, video_title: str, reason: str):
    """单次评论失败通知（不同于连续失败）"""
    if self._baidu_bot:
        try:
            self._baidu_bot.notify_comment_failed(
                video_title=video_title,
                reason=reason,
                slot_id=int(slot_id)
            )
        except Exception as e:
            logger.error(f"[通知管理器] 百度机器人通知失败: {e}")
```

#### 3.3 任务开始通知
```python
def notify_task_started(self, slot_id: str, task_type: str, target_count: int):
    """任务开始通知"""
    title = f"实例 {slot_id} 任务开始"
    message = f"{task_type}，目标数量: {target_count}"
    self.send_notification(...)

    if self._baidu_bot:
        self._baidu_bot.notify_task_started(
            task_type=task_type,
            target_count=target_count,
            slot_id=int(slot_id)
        )
```

#### 3.4 任务完成通知
```python
def notify_task_completed(self, slot_id: str, task_type: str, success_count: int, total_count: int):
    """任务完成通知"""
    title = f"实例 {slot_id} 任务完成"
    message = f"{task_type}，完成情况: {success_count}/{total_count}"
    self.send_notification(...)

    if self._baidu_bot:
        self._baidu_bot.notify_task_completed(
            task_type=task_type,
            success_count=success_count,
            total_count=total_count,
            slot_id=int(slot_id)
        )
```

#### 3.5 CD 限制通知
```python
def notify_cd_limit(self, slot_id: str, cd_warmup_hours: int):
    """CD 限制通知"""
    title = f"实例 {slot_id} 触发 CD 限制"
    message = f"将进入 {cd_warmup_hours} 小时养号模式"
    self.send_notification(...)

    if self._baidu_bot:
        self._baidu_bot.notify_cd_limit(
            cd_warmup_hours=cd_warmup_hours,
            slot_id=int(slot_id)
        )
```

---

### 4. 在 main.py 中调用通知方法 ✅

**文件**: `app/main.py`

#### 4.1 任务开始通知
```python
# Line 361-369
if not keywords:
    logger.warning("配置中未找到搜索关键词，任务终止")
    return

# 发送任务开始通知
notification_mgr.notify_task_started(
    slot_id=slot_id,
    task_type="评论任务",
    target_count=target_count
)
```

#### 4.2 评论成功/失败通知
```python
# Line 653-675
if result == "success":
    history_mgr.add(video_info['bv'])
    total_success += 1
    notification_mgr.reset_failure_count(slot_id)
    reset_retry_count(slot_id, "comment")

    # 发送评论成功通知（百度机器人）
    notification_mgr.notify_comment_success(
        slot_id=slot_id,
        video_title=video_info.get('title', '未知视频'),
        comment_text=text
    )
else:
    # 失败时记录（连续3次失败会自动发送通知）
    notification_mgr.notify_failure(slot_id, toast_message or "评论失败")

    # 发送单次评论失败通知（百度机器人）
    notification_mgr.notify_comment_failed(
        slot_id=slot_id,
        video_title=video_info.get('title', '未知视频'),
        reason=toast_message or "评论失败"
    )
```

#### 4.3 CD 限制通知
```python
# Line 614-615 (替换原有的 send_notification)
# 发送通知
notification_mgr.notify_cd_limit(slot_id, cd_warmup_hours)
```

#### 4.4 任务完成通知
```python
# Line 708-720
if cd_limit_triggered:
    logger.warning(f"任务因触发 CD 限制而终止。本次成功评论: {total_success}/{target_count}")
elif captcha_terminated:
    logger.info(f"任务因验证码次数达上限而终止。本次成功评论: {total_success}/{target_count}")
else:
    logger.info(f"所有任务已完成。本次成功评论: {total_success}/{target_count}")

# 发送任务完成通知
notification_mgr.notify_task_completed(
    slot_id=slot_id,
    task_type="评论任务",
    success_count=total_success,
    total_count=target_count
)
```

---

## 通知类型对照表

| 通知类型 | 配置键 | 触发时机 | 实现状态 |
|---------|--------|---------|---------|
| 验证码提醒 | `captcha_alert` | 检测到验证码 | ✅ 已实现 |
| 验证码冷却 | `captcha_cooldown` | 验证码冷却开始 | ✅ 已实现 |
| 验证码达上限 | `captcha_terminated` | 验证码次数达上限 | ✅ 已实现 |
| CD 限制 | `cd_limit` | 触发 CD 限制 | ✅ 已修复 |
| 评论成功 | `comment_success` | 每次评论成功 | ✅ 已修复 |
| 评论失败 | `comment_failed` | 每次评论失败 | ✅ 已修复 |
| 任务开始 | `task_started` | 任务开始时 | ✅ 已修复 |
| 任务完成 | `task_completed` | 任务完成时 | ✅ 已修复 |
| 任务错误 | `task_error` | 任务异常终止 | ✅ 已实现 |

---

## 配置示例

```yaml
bots:
  baidu:
    enabled: true
    api_url: "http://apiin.im.baidu.com/api/msg/groupmsgsend"
    access_token: "your_access_token_here"
    group_id: "your_group_id_here"
    notifications:
      captcha_alert: true          # 验证码提醒
      captcha_cooldown: true       # 验证码冷却通知
      captcha_terminated: true     # 验证码达上限通知
      cd_limit: true               # CD 限制通知
      comment_success: false       # 评论成功通知（建议关闭，太频繁）
      comment_failed: true         # 评论失败通知
      task_started: true           # 任务开始通知
      task_completed: true         # 任务完成通知
      task_error: true             # 任务错误通知
```

---

## 测试验证

### 1. 配置加载测试
```bash
python -c "
import sys
sys.path.insert(0, 'app')
from core.slot import get_config_path
from core.config import ConfigValidator

config = ConfigValidator.load_config(get_config_path('0'))
baidu = config.get('bots', {}).get('baidu', {})

print('Enabled:', baidu.get('enabled'))
print('API URL:', baidu.get('api_url'))
print('Group ID:', baidu.get('group_id'))
print('Notifications:', baidu.get('notifications'))
"
```

### 2. 通知管理器测试
```bash
python -c "
import sys
sys.path.insert(0, 'app')
from core.slot import get_config_path
from core.config import ConfigValidator
from core.notification_manager import NotificationManager

config = ConfigValidator.load_config(get_config_path('0'))
mgr = NotificationManager()
mgr.update_config(config)

print('Baidu bot initialized:', mgr._baidu_bot is not None)
print('Baidu bot enabled:', mgr._baidu_bot.enabled if mgr._baidu_bot else False)
"
```

### 3. 完整流程测试
运行评论任务，观察日志输出：
```
[通知管理器] 百度机器人已启用
[实例 0] 任务开始: 评论任务，目标数量: 2
[实例 0] 评论成功: 视频: xxx, 评论: xxx
[实例 0] 任务完成: 评论任务，完成情况: 2/2
```

---

## 注意事项

### 1. 内网环境要求
百度如流机器人 API (`apiin.im.baidu.com`) 只能在百度内网访问：
- 需要在百度办公室或连接百度 VPN
- 外网测试会返回 502 Bad Gateway

### 2. 通知频率控制
- `comment_success` 建议设置为 `false`，避免消息过于频繁
- `comment_failed` 建议保持 `true`，及时发现问题
- 连续失败 3 次会额外发送警告通知

### 3. 配置更新
如果修改了 `bots` 配置，需要：
1. 重启任务（停止后重新开始）
2. 或者重启 Web 服务

---

## 修复文件清单

- [x] `app/core/config.py` - 配置加载修复
- [x] `app/core/notification_manager.py` - 添加通知方法
- [x] `app/main.py` - 初始化和调用通知
- [x] `用户数据/config.yaml` - 添加 bots 配置段

---

## 后续优化建议

1. **配置验证**: 在 `ConfigValidator` 中添加 `bots` 配置的默认值和验证
2. **错误重试**: 百度机器人通知失败时可以考虑重试机制
3. **通知队列**: 对于高频通知（如评论成功），可以考虑批量发送
4. **外网支持**: 如果百度提供外网 API，可以添加配置选项

---

**修复完成时间**: 2026-03-04
**测试状态**: ✅ 配置加载正常，通知方法已集成
**生产验证**: ⏳ 需要在百度内网环境验证实际推送
