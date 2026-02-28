# Bilibili Bot v3.7.1 GUI 启动器修复

## 修复内容

### 🐛 Bug 修复

#### 1. 自动打开两个浏览器窗口 ✅

**问题描述：**
- GUI 启动器启动后会自动打开两个浏览器窗口
- 一个来自 `launcher_gui.py`
- 另一个来自 `web/app.py` 的 lifespan 函数

**根本原因：**
- `web/app.py` 在 frozen 模式下会自动打开浏览器
- `launcher_gui.py` 也会自动打开浏览器
- 两者冲突导致打开两次

**修复方案：**
- 禁用 `web/app.py` 中的自动打开浏览器逻辑
- 仅由 `launcher_gui.py` 控制浏览器打开
- 避免重复打开

**修改文件：**
- `app/web/app.py` (第143-151行) - 移除自动打开浏览器代码

---

#### 2. 运行日志缺少访问地址提示 ✅

**问题描述：**
- 启动器日志中没有明确提示用户访问地址
- 用户不知道如何进入控制台

**修复方案：**
- 在后端启动成功后，日志中显示：
  ```
  后端服务已启动
  请访问以下地址进入控制台:
    http://localhost:9527/panel/
  ```

**修改文件：**
- `app/launcher_gui.py` (第338-345行) - 添加访问地址提示

---

#### 3. 停止服务后前端仍在运行 ✅

**问题描述：**
- 点击"停止服务"按钮后，前端页面仍然可以访问
- uvicorn server 没有正确停止
- 只是设置了标志位，但线程仍在运行

**根本原因：**
- 原代码使用 `uvicorn.run()` 直接运行，无法控制停止
- 只设置 `self.backend_running = False`，但 uvicorn 不会停止
- 需要使用 `uvicorn.Server` 实例来控制生命周期

**修复方案：**
1. 使用 `uvicorn.Server` 和 `uvicorn.Config` 创建可控制的 server
2. 保存 server 实例到 `self.backend_server`
3. 停止时设置 `server.should_exit = True`
4. 关闭窗口时也正确停止 server

**修改文件：**
- `app/launcher_gui.py` (多处修改)
  - 第53行：添加 `self.backend_server = None`
  - 第315-337行：修改 `_run_backend` 使用 Server 实例
  - 第367-383行：修改 `stop_backend` 正确停止 server
  - 第386-397行：修改 `on_closing` 正确停止 server

---

## 技术细节

### uvicorn 停止机制

**修复前（错误）：**
```python
def _run_backend(self):
    self.backend_running = True
    uvicorn.run(app, host="0.0.0.0", port=PORT)  # 无法停止

def stop_backend(self):
    self.backend_running = False  # 只设置标志，server 仍在运行
```

**修复后（正确）：**
```python
def _run_backend(self):
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT)
    self.backend_server = uvicorn.Server(config)
    self.backend_running = True
    self.backend_server.run()  # 可控制的 server

def stop_backend(self):
    self.backend_running = False
    if self.backend_server:
        self.backend_server.should_exit = True  # 正确停止 server
```

### 浏览器打开控制

**修复前：**
- `web/app.py` lifespan: 自动打开浏览器（frozen 模式）
- `launcher_gui.py`: 自动打开浏览器
- 结果：打开两次

**修复后：**
- `web/app.py` lifespan: 不再自动打开
- `launcher_gui.py`: 仅打开一次
- 结果：只打开一次

---

## 测试验证

### 测试 1: 浏览器打开次数
1. 启动 GUI 启动器
2. 验证 License
3. 点击"启动服务"
4. **预期**：只打开一个浏览器窗口
5. **实际**：✅ 只打开一个窗口

### 测试 2: 日志提示
1. 启动服务
2. 查看运行日志
3. **预期**：显示访问地址提示
4. **实际**：✅ 显示完整提示

### 测试 3: 停止服务
1. 启动服务
2. 访问 Web 面板
3. 点击"停止服务"
4. 刷新浏览器页面
5. **预期**：页面无法访问（连接被拒绝）
6. **实际**：✅ 服务已停止，无法访问

### 测试 4: 关闭窗口
1. 启动服务
2. 直接关闭启动器窗口
3. 确认退出
4. 刷新浏览器页面
5. **预期**：页面无法访问
6. **实际**：✅ 服务已停止

---

## 部署步骤

1. **重新打包启动器**：
```bash
python -m PyInstaller launcher.spec --clean
```

2. **或创建完整便携版**：
```bash
build_portable.bat
```

---

## 版本信息
- 版本：v3.7.1
- 更新日期：2026-02-28
- 修复类型：GUI 启动器优化
