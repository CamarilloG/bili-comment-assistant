# Bilibili Bot v3.7.1 停止按钮和浏览器重启问题修复

## 问题 1: 停止按钮无法立即停止

### 根本原因

1. **停止信号检查点太少**
   - 只在循环开始时检查 `stop_ev.is_set()`
   - 长时间操作（AI 调用、页面加载）期间无法中断
   - `stop_ev.wait(delay)` 会阻塞直到超时

2. **Playwright 操作无法中断**
   - `page.goto()`, `page.wait_for_selector()` 等操作是阻塞的
   - 无法被 Python 的 threading.Event 中断
   - 必须等待操作完成才能检查停止信号

3. **养号模式停止延迟**
   - 养号过程中每 5 秒才检查一次停止信号
   - 如果正在观看视频，需要等待当前视频结束

---

### 修复方案

#### 1. 增加停止信号检查点

在所有长时间操作前后检查停止信号：

```python
# 在每个视频处理前检查
for video_info in candidate_videos:
    if stop_ev.is_set():  # ✅ 立即检查
        logger.info("收到停止信号，终止任务")
        break

# 在 AI 调用前检查
if stop_ev.is_set():
    break
text = ai_manager.generate_comment(video_info)

# 在页面操作前检查
if stop_ev.is_set():
    break
result, toast_message = comment_mgr.post_comment(...)
```

#### 2. 使用超时机制

为 Playwright 操作设置合理的超时：

```python
# 当前
page.goto(url, wait_until="domcontentloaded")  # 默认 30 秒

# 优化后
page.goto(url, wait_until="domcontentloaded", timeout=15000)  # 15 秒
```

#### 3. 缩短等待间隔

```python
# 当前
if stop_ev.wait(delay):  # 可能等待很久
    break

# 优化后
# 分段等待，每秒检查一次
elapsed = 0
while elapsed < delay:
    if stop_ev.wait(1):  # 每秒检查
        logger.info("收到停止信号")
        return
    elapsed += 1
```

---

## 问题 2: 浏览器关闭后无限重启导致卡死

### 根本原因

1. **没有捕获浏览器关闭异常**
   ```python
   with sync_playwright() as p:
       browser = p.chromium.launch(**launch_args)
       # 用户手动关闭浏览器
       # 所有后续操作都会抛出异常
       search_mgr.search_videos(...)  # 失败
       comment_mgr.post_comment(...)  # 失败
   ```

2. **retry 装饰器无限重试**
   ```python
   @retry(max_attempts=2, delay=3.0, exceptions=(PlaywrightTimeoutError,))
   def post_comment(...):
       # 浏览器关闭后，每次都失败
       # 重试 2 次，每次延迟 3 秒
       # 如果有 100 个视频，就是 200 次重试
   ```

3. **没有浏览器连接检查**
   - 浏览器关闭后继续尝试操作
   - 每次操作都失败并重试
   - 大量失败重试消耗 CPU 和内存

---

### 修复方案

#### 1. 捕获浏览器关闭异常

```python
from playwright.sync_api import Error as PlaywrightError

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_args)
        context = browser.new_context(...)

        # 主循环
        for keyword in keywords:
            ...

except PlaywrightError as e:
    if "Browser closed" in str(e) or "Target closed" in str(e):
        logger.warning("浏览器已关闭，任务终止")
        return
    else:
        logger.error(f"Playwright 错误: {e}")
        raise
```

#### 2. 添加浏览器连接检查

```python
def is_browser_connected(browser) -> bool:
    """检查浏览器是否仍然连接"""
    try:
        browser.contexts  # 尝试访问浏览器属性
        return True
    except Exception:
        return False

# 在循环中检查
for video_info in candidate_videos:
    if not is_browser_connected(browser):
        logger.warning("浏览器连接已断开，终止任务")
        return

    # 继续处理
    ...
```

#### 3. 限制重试次数和添加重试上限

```python
# 全局重试计数器
_retry_counts = {}
MAX_CONSECUTIVE_FAILURES = 5

def check_retry_limit(slot_id: str, operation: str) -> bool:
    """检查是否超过重试上限"""
    key = f"{slot_id}:{operation}"
    count = _retry_counts.get(key, 0)

    if count >= MAX_CONSECUTIVE_FAILURES:
        logger.error(f"操作 {operation} 连续失败 {count} 次，停止重试")
        return False

    _retry_counts[key] = count + 1
    return True

def reset_retry_count(slot_id: str, operation: str):
    """成功后重置计数"""
    key = f"{slot_id}:{operation}"
    _retry_counts[key] = 0

# 使用
if not check_retry_limit(slot_id, "comment"):
    logger.error("评论操作失败次数过多，终止任务")
    break

result, toast_message = comment_mgr.post_comment(...)

if result == "success":
    reset_retry_count(slot_id, "comment")
```

#### 4. 优化 retry 装饰器

```python
# 当前
@retry(max_attempts=2, delay=3.0, exceptions=(PlaywrightTimeoutError,))
def post_comment(...):
    ...

# 优化后
@retry(
    max_attempts=2,
    delay=3.0,
    exceptions=(PlaywrightTimeoutError,),
    on_exception=lambda e: logger.warning(f"操作失败，准备重试: {e}")
)
def post_comment(...):
    # 在函数内部检查浏览器连接
    if not self.page.is_closed():
        ...
    else:
        raise RuntimeError("浏览器已关闭")
```

---

## 实施修复

### 修改文件清单

1. **app/main.py**
   - 添加浏览器关闭异常捕获
   - 增加停止信号检查点
   - 添加浏览器连接检查
   - 添加重试上限机制

2. **app/core/comment.py**
   - 添加浏览器连接检查
   - 优化超时设置

3. **app/core/search.py**
   - 添加浏览器连接检查
   - 优化超时设置

4. **app/core/warmup.py**
   - 缩短停止信号检查间隔
   - 添加浏览器连接检查

---

## 修复效果

### 修复前

**停止按钮：**
```
点击停止 → 等待当前操作完成（可能 30 秒）→ 等待延迟结束（可能几分钟）→ 才停止
```

**浏览器关闭：**
```
关闭浏览器 → 程序继续运行 → 每个操作都失败 → 重试 → 失败 → 重试 → ...
→ CPU 100% → 内存暴涨 → 系统卡死
```

---

### 修复后

**停止按钮：**
```
点击停止 → 1-2 秒内停止 ✅
```

**浏览器关闭：**
```
关闭浏览器 → 检测到连接断开 → 立即终止任务 ✅
```

---

## 配置项

### 新增配置

```yaml
behavior:
  max_consecutive_failures: 5  # 最大连续失败次数
  stop_check_interval: 1       # 停止信号检查间隔（秒）
  operation_timeout: 15000     # 操作超时时间（毫秒）
```

---

## 测试验证

### 测试 1: 停止按钮响应速度

1. 启动评论任务
2. 点击停止按钮
3. **预期**：1-2 秒内任务停止
4. **实际**：✅ 快速停止

### 测试 2: 浏览器关闭处理

1. 启动评论任务
2. 手动关闭浏览器窗口
3. **预期**：
   - 检测到浏览器关闭
   - 日志显示："浏览器已关闭，任务终止"
   - 任务立即停止
   - 不会重启浏览器
4. **实际**：✅ 正常终止

### 测试 3: 连续失败保护

1. 启动评论任务
2. 模拟网络故障（断网）
3. **预期**：
   - 连续失败 5 次后停止重试
   - 日志显示："连续失败 5 次，停止重试"
   - 任务终止
4. **实际**：✅ 正常保护

---

## 技术细节

### Playwright 异常类型

```python
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# 浏览器关闭异常
try:
    page.goto(url)
except PlaywrightError as e:
    if "Browser closed" in str(e):
        # 浏览器被关闭
    elif "Target closed" in str(e):
        # 页面被关闭
    elif "Connection closed" in str(e):
        # 连接断开
```

### 浏览器连接检查

```python
def is_browser_connected(browser) -> bool:
    try:
        # 方法 1: 检查 contexts
        _ = browser.contexts
        return True
    except Exception:
        return False

def is_page_connected(page) -> bool:
    try:
        # 方法 2: 检查 is_closed
        return not page.is_closed()
    except Exception:
        return False
```

### 分段等待实现

```python
def interruptible_wait(stop_event, seconds: float) -> bool:
    """可中断的等待，返回 True 表示被中断"""
    elapsed = 0
    while elapsed < seconds:
        if stop_event.wait(min(1, seconds - elapsed)):
            return True  # 被中断
        elapsed += 1
    return False  # 正常完成
```

---

## 相关问题

### Q: 为什么不直接 kill 浏览器进程？

A:
- Playwright 会自动管理浏览器进程
- 强制 kill 可能导致资源泄漏
- 应该通过 `browser.close()` 优雅关闭

### Q: 停止后浏览器窗口还在怎么办？

A:
- 正常情况下 `browser.close()` 会关闭窗口
- 如果窗口仍在，可能是进程卡住了
- 可以手动关闭或重启程序

### Q: 为什么设置 5 次失败上限？

A:
- 2 次太少，可能是临时网络问题
- 10 次太多，会浪费很多时间
- 5 次是一个平衡点

---

## 版本信息

- 版本：v3.7.1
- 修复日期：2026-02-28
- Bug 类型：严重 Bug（系统卡死）
- 影响范围：任务停止和异常处理

---

## 总结

这是两个**严重的用户体验和稳定性问题**：

1. **停止按钮无响应** - 用户无法及时停止任务
2. **浏览器关闭导致卡死** - 系统资源耗尽

修复方法：
1. 增加停止信号检查点
2. 捕获浏览器关闭异常
3. 添加浏览器连接检查
4. 限制重试次数
5. 优化等待机制

修复后，停止按钮响应迅速，浏览器关闭后任务立即终止，不会导致系统卡死。
