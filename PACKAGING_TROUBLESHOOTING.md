# 打包后启动失败问题排查指南

## 问题描述
打包后的 `BiliBotLauncher_v3.7.1.exe` 在客户机上运行时，后端服务启动失败。

---

## 排查步骤

### 1. 使用调试版本

首先使用带控制台的调试版本来查看详细错误信息：

```bash
# 打包调试版本
build_launcher_debug.bat
```

调试版本会显示控制台窗口，可以看到详细的错误堆栈。

---

### 2. 常见问题及解决方案

#### 问题 1: 缺少 Python 运行环境

**症状：**
```
[14:55:15] 正在启动后端服务...
[14:55:17] 后端服务启动失败
```

**原因：**
- 便携版需要 `python` 文件夹
- 客户机上缺少 Python 环境

**解决方案：**
```bash
# 确保 python 文件夹存在
BiliBot_v3.7.1_Portable/
├── BiliBotLauncher_v3.7.1.exe
├── python/                    # 必须存在
│   ├── python.exe
│   ├── python311.dll
│   └── Lib/
```

---

#### 问题 2: 缺少依赖模块

**症状：**
```
模块导入失败: No module named 'xxx'
```

**原因：**
- PyInstaller 未正确打包某些模块
- `hiddenimports` 列表不完整

**解决方案：**
1. 检查 `launcher.spec` 中的 `hiddenimports` 列表
2. 添加缺失的模块
3. 重新打包

---

#### 问题 3: 前端文件缺失

**症状：**
```
后端启动成功，但访问 /panel/ 显示 404
```

**原因：**
- 前端 dist 文件未正确打包
- `datas` 配置错误

**解决方案：**
检查 `launcher.spec` 中的 `datas` 配置：
```python
datas=[
    ('app\\web\\frontend-v2\\dist', 'web\\frontend-v2\\dist'),
    ('app\\web\\frontend-v2\\dist\\assets', 'web\\frontend-v2\\dist\\assets'),
],
```

---

#### 问题 4: 端口被占用

**症状：**
```
[Errno 10048] error while attempting to bind on address ('0.0.0.0', 9527)
```

**原因：**
- 端口 9527 已被其他程序占用

**解决方案：**
```bash
# 检查端口占用
netstat -ano | findstr 9527

# 结束占用进程
taskkill /PID <进程ID> /F
```

---

#### 问题 5: 配置文件缺失

**症状：**
```
Configuration error: [Errno 2] No such file or directory: 'config.yaml'
```

**原因：**
- 缺少 `config.yaml` 配置文件

**解决方案：**
```bash
# 复制配置模板
copy config.template.yaml config.yaml
```

---

### 3. 完整的打包检查清单

#### 打包前检查

- [ ] 前端已构建：`cd app/web/frontend-v2 && npm run build`
- [ ] `launcher.spec` 包含所有模块
- [ ] `version_info.txt` 存在
- [ ] 图标文件存在

#### 打包后检查

- [ ] `dist\BiliBotLauncher_v3.7.1.exe` 存在
- [ ] 文件大小合理（通常 > 50MB）
- [ ] 在本机测试运行成功

#### 便携版检查

- [ ] `python` 文件夹完整
- [ ] `config.yaml` 存在
- [ ] `license.lic` 存在
- [ ] `使用说明.txt` 存在

---

### 4. 调试技巧

#### 启用详细日志

在 `launcher_gui.py` 中已添加详细日志：

```python
self.log("正在导入 web.app 模块...")
self.log("正在导入 uvicorn 模块...")
self.log("正在创建 uvicorn 配置...")
self.log("正在创建 uvicorn server...")
self.log("正在启动 uvicorn server...")
```

#### 查看完整错误堆栈

调试版本会显示完整的 traceback：

```python
except Exception as e:
    error_msg = f"后端启动失败: {e}\n{traceback.format_exc()}"
    self.log(error_msg)
    traceback.print_exc()
```

#### 检查模块路径

在日志中会显示 `sys.path`：

```python
error_msg = f"模块导入失败: {e}\n模块路径: {sys.path}"
```

---

### 5. 测试流程

#### 本机测试

1. 打包调试版本
2. 运行 `dist\BiliBotLauncher_v3.7.1.exe`
3. 查看控制台输出
4. 确认后端启动成功

#### 客户机测试

1. 复制整个 `BiliBot_v3.7.1_Portable` 文件夹
2. 确保包含 `python` 文件夹
3. 放置 `license.lic` 文件
4. 运行 `BiliBotLauncher_v3.7.1.exe`
5. 查看日志窗口的错误信息

---

### 6. 已知问题

#### PyInstaller 打包问题

**问题：** 某些动态导入的模块可能未被打包

**解决方案：** 在 `hiddenimports` 中显式声明所有模块

#### Playwright 浏览器驱动

**问题：** Playwright 需要额外的浏览器驱动

**解决方案：**
- 使用系统已安装的 Chrome/Edge
- 或在 `python` 文件夹中包含 Playwright 驱动

#### 防火墙/杀毒软件

**问题：** 可能被误报为病毒

**解决方案：**
- 添加信任
- 使用代码签名证书

---

### 7. 快速修复方案

如果打包版本无法使用，可以使用以下临时方案：

#### 方案 1: 使用 Python 环境直接运行

```bash
# 确保安装了 Python 3.11
python app/launcher_gui.py
```

#### 方案 2: 使用 Web 单文件版

```bash
# 打包 Web 单文件版
build_web_exe.bat

# 运行
dist\BiliBot_Web_V3_7.exe
```

#### 方案 3: 使用批处理启动

```bash
# 创建 start.bat
@echo off
cd /d "%~dp0"
python\python.exe app\run_web.py
pause
```

---

### 8. 联系支持

如果以上方法都无法解决问题，请提供以下信息：

1. **错误日志**（完整的控制台输出）
2. **系统信息**（Windows 版本、Python 版本）
3. **文件列表**（`dir /s` 输出）
4. **端口占用情况**（`netstat -ano | findstr 9527`）

---

## 更新记录

- 2026-02-28: 创建文档
- 2026-02-28: 添加调试版本打包脚本
- 2026-02-28: 更新 hiddenimports 列表
