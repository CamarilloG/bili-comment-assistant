# Bilibili Bot v3.7.1 CD 限制无限重试 Bug 修复

## 问题描述

**Bug：** 触发 CD 限制后，养号结束继续评论，如果再次触发 CD 限制会无限重试。

**症状：**
1. 第一次评论触发 CD 限制 → 养号 60 分钟
2. 养号结束后继续评论
3. 再次触发 CD 限制 → 又养号 60 分钟
4. 无限循环...

**影响：**
- 账号可能被永久限制
- 浪费大量时间在养号上
- 无法自动停止任务

---

## 根本原因

### 原有逻辑

```python
if result == "cd_limit":
    # 养号 60 分钟
    warmup_mgr.run(duration_override=60)

    # 增大延迟倍率
    delay_multiplier *= 2.0

    # 继续下一个视频 ❌
    continue
```

**问题：**
- `continue` 会继续循环，尝试下一个视频
- 如果再次触发 CD 限制，又会养号 60 分钟
- 没有终止条件，会无限重试

---

## 修复方案

### 新逻辑

**策略：** 只要触发 CD 限制，就进入长时间养号（默认 3 小时），养号结束后直接停止任务。

```python
if result == "cd_limit":
    # 设置 CD 限制标志
    cd_limit_triggered = True

    # 发送通知
    notification_mgr.send_notification(
        title=f"实例 {slot_id} 触发 CD 限制",
        message="将进入 3 小时养号模式，养号结束后自动停止任务",
        notification_type="warning",
        slot_id=slot_id,
        show_system=True,
    )

    # 进入 3 小时养号模式
    cd_warmup_hours = config["captcha"].get("cd_warmup_hours", 3)
    warmup_mgr.run(duration_override=cd_warmup_hours * 60)

    # 跳出循环，终止任务 ✅
    break
```

---

## 修改内容

### 1. 添加 CD 限制标志

**文件：** `app/main.py`

```python
# 添加标志变量
cd_limit_triggered = False

# 循环条件中检查标志
while total_success < target_count and not stop_ev.is_set() and not captcha_terminated and not cd_limit_triggered:
    ...

# 外层循环也检查
for keyword in keywords:
    if stop_ev.is_set() or captcha_terminated or cd_limit_triggered: break
```

---

### 2. 修改 CD 限制处理逻辑

**文件：** `app/main.py` 第 471-507 行

**修改前：**
```python
if result == "cd_limit":
    # 养号 60 分钟
    warmup_mgr.run(duration_override=60)

    # 增大延迟倍率
    delay_multiplier *= 2.0

    # 继续下一个视频
    continue
```

**修改后：**
```python
if result == "cd_limit":
    # 设置标志
    cd_limit_triggered = True

    # 发送通知
    notification_mgr.send_notification(...)

    # 养号 3 小时（可配置）
    cd_warmup_hours = config["captcha"].get("cd_warmup_hours", 3)
    warmup_mgr.run(duration_override=cd_warmup_hours * 60)

    # 终止任务
    break
```

---

### 3. 添加配置项

**文件：** `app/config.template.yaml`

```yaml
captcha:
  max_count: 3           # 每日最大验证码次数
  quiet_minutes: 5       # 验证码后静默等待时间（分钟）
  warmup_minutes: 30     # 验证码后养号基础时长（分钟）
  cd_warmup_hours: 3     # CD限制后养号时长（小时），养号结束后自动停止任务
```

**文件：** `app/core/config.py`

```python
DEFAULT_CONFIG = {
    "captcha": {
        "max_count": 3,
        "quiet_minutes": 5,
        "warmup_minutes": 30,
        "cd_warmup_hours": 3  # 新增
    }
}

# 验证逻辑
if "cd_warmup_hours" in captcha:
    validated["captcha"]["cd_warmup_hours"] = max(1, int(captcha["cd_warmup_hours"]))
```

---

### 4. 更新任务结束日志

**文件：** `app/main.py`

```python
if cd_limit_triggered:
    logger.warning(f"任务因触发 CD 限制而终止。本次成功评论: {total_success}/{target_count}")
elif captcha_terminated:
    logger.info(f"任务因验证码次数达上限而终止。本次成功评论: {total_success}/{target_count}")
else:
    logger.info(f"所有任务已完成。本次成功评论: {total_success}/{target_count}")
```

---

## 修复效果

### 修复前

```
评论 1 → 成功
评论 2 → CD 限制 → 养号 60 分钟
评论 3 → CD 限制 → 养号 60 分钟
评论 4 → CD 限制 → 养号 60 分钟
...
无限循环 ❌
```

### 修复后

```
评论 1 → 成功
评论 2 → CD 限制 → 养号 3 小时 → 任务停止 ✅
```

---

## 通知功能

触发 CD 限制时会发送：

1. **Web 吐司通知**
   - 标题：实例 X 触发 CD 限制
   - 内容：将进入 3 小时养号模式，养号结束后自动停止任务
   - 类型：警告（黄色）

2. **Windows 系统通知**
   - 同样的标题和内容
   - 重要事件，必须显示

3. **日志输出**
   ```
   [风控CD] 触发 CD 限制，进入 3 小时养号模式...
   [风控CD] 养号结束后将自动停止任务，不再继续评论
   [风控CD] 3 小时养号完成，任务即将停止
   任务因触发 CD 限制而终止。本次成功评论: 5/20
   ```

---

## 配置说明

### cd_warmup_hours 参数

**默认值：** 3 小时

**推荐值：**
- 轻度 CD 限制：2-3 小时
- 中度 CD 限制：3-6 小时
- 重度 CD 限制：6-12 小时

**注意：**
- 最小值：1 小时
- 养号期间可以手动停止任务
- 养号结束后任务会自动停止，不会继续评论

---

## 与验证码冷却的区别

### 验证码冷却

**触发条件：** 检测到验证码

**处理流程：**
1. 静默等待 5 分钟
2. 养号 30-90 分钟（根据次数递增）
3. 增大延迟倍率 1.5 倍
4. **继续评论任务** ✅

**原因：** 验证码可能是偶然触发，解决后可以继续

---

### CD 限制冷却

**触发条件：** 检测到 "CD时间未到不能评论"

**处理流程：**
1. 养号 3 小时（可配置）
2. **直接停止任务** ✅

**原因：** CD 限制说明账号已被严格限制，继续评论只会加重风控

---

## 测试验证

### 测试场景 1: 首次触发 CD 限制

1. 启动评论任务
2. 触发 CD 限制
3. **预期**：
   - 显示通知："将进入 3 小时养号模式"
   - 开始养号
   - 养号结束后任务停止
   - 日志显示："任务因触发 CD 限制而终止"

### 测试场景 2: 养号期间手动停止

1. 触发 CD 限制，开始养号
2. 手动点击"停止任务"
3. **预期**：
   - 养号立即停止
   - 任务终止

### 测试场景 3: 配置自定义时长

1. 修改 `config.yaml`：`cd_warmup_hours: 6`
2. 触发 CD 限制
3. **预期**：
   - 养号 6 小时
   - 养号结束后任务停止

---

## 部署步骤

### 1. 代码已修复

- ✅ `app/main.py` - 添加 CD 限制标志和终止逻辑
- ✅ `app/config.template.yaml` - 添加 `cd_warmup_hours` 配置
- ✅ `app/core/config.py` - 支持新配置项

### 2. 更新配置文件（可选）

如果想自定义 CD 限制后的养号时长：

```yaml
captcha:
  cd_warmup_hours: 3  # 修改为你想要的小时数
```

### 3. 重新构建前端

```bash
cd app/web/frontend-v2
npm run build
```

### 4. 重新打包（如需）

```bash
build_portable.bat
```

---

## 技术细节

### 标志变量的作用

```python
cd_limit_triggered = False  # 初始化

if result == "cd_limit":
    cd_limit_triggered = True  # 设置标志
    break  # 跳出内层循环

# 外层循环检查标志
for keyword in keywords:
    if cd_limit_triggered: break  # 跳出外层循环

# 最终检查
if cd_limit_triggered:
    logger.warning("任务因触发 CD 限制而终止")
```

**作用：**
- 确保任务完全停止
- 不会继续处理下一个关键词
- 不会继续翻页

---

### 养号时长计算

```python
cd_warmup_hours = 3  # 小时
duration_minutes = cd_warmup_hours * 60  # 转换为分钟

warmup_mgr.run(duration_override=duration_minutes)
```

**WarmupManager 接受的参数：**
- `duration_override`: 分钟数
- 例如：3 小时 = 180 分钟

---

## 相关问题

### Q: 为什么 CD 限制要停止任务，而验证码不停止？

A:
- **验证码**：可能是偶然触发，解决后可以继续
- **CD 限制**：说明账号已被严格限制，继续评论会加重风控，甚至导致永久封禁

### Q: 3 小时够吗？会不会太短？

A:
- 3 小时是保守的默认值
- 可以根据实际情况调整 `cd_warmup_hours`
- 建议：首次触发用 3 小时，如果频繁触发可以增加到 6-12 小时

### Q: 养号期间可以手动停止吗？

A: 可以。点击"停止任务"会立即停止养号。

### Q: 养号结束后会自动重启任务吗？

A: 不会。养号结束后任务完全停止，需要手动重新启动。

---

## 版本信息

- 版本：v3.7.1
- 修复日期：2026-02-28
- Bug 类型：逻辑 Bug（无限重试）
- 影响范围：CD 限制处理

---

## 总结

这是一个**严重的逻辑 Bug**，会导致账号在 CD 限制状态下无限重试，加重风控。

**修复方法：**
1. 添加 `cd_limit_triggered` 标志
2. 触发 CD 限制后直接 `break` 终止任务
3. 养号时长增加到 3 小时（可配置）
4. 发送通知提醒用户

修复后，触发 CD 限制会立即进入长时间养号，养号结束后自动停止任务，避免加重风控。
