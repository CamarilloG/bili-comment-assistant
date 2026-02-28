# Web 版单文件 exe 打包实现说明

本文档整理 B 站评论助手 Web 控制面板（uvicorn + FastAPI）打包为**单文件 exe** 的最终实现方式，便于后续维护与复现。

---

## 1. 目标与约束

| 项目 | 说明 |
|------|------|
| **入口** | 与 `start.bat` 等价：`uvicorn web.app:app --host 0.0.0.0 --port 9527` |
| **产出** | 单个 exe，双击即可运行 |
| **配置** | `config.yaml`、`cookies.json` 等放在 **exe 同目录**，便于用户修改 |
| **首次运行** | 同目录无配置时自动创建 `config.yaml`（默认值）和 `cookies.json`（`[]`）；若 `browser.path` 为空且为 Windows，自动从注册表读取默认浏览器路径并写入配置 |
| **浏览器** | 启动后自动用系统默认浏览器打开 `http://localhost:9527/panel/` |
| **错误** | 异常时不闪退：控制台输出 + 同目录 `run_web_error.log` + 按回车退出 |

---

## 2. 涉及文件一览

| 文件 | 作用 |
|------|------|
| `app/run_web.py` | exe 入口脚本（PyInstaller 入口） |
| `run_web.spec` | PyInstaller 打包配置（项目根目录） |
| `app/web/app.py` | 静态资源路径 frozen 支持 + 启动后自动打开浏览器 |
| `app/server/api.py` | `server/static` 路径 frozen 支持 |

---

## 3. 入口脚本：`app/run_web.py`

### 3.1 工作目录与 sys.path

- **frozen（exe）**：`app_base = os.path.dirname(sys.executable)`，并 `os.chdir(app_base)`。**不**修改 `sys.path`，避免干扰 PyInstaller 对打包模块的查找。
- **非 frozen**：`app_base = 脚本所在目录`，chdir 到该目录，并将 `app_base` 加入 `sys.path`，便于直接 `python run_web.py` 时能找到 `web`。

### 3.2 首次运行创建配置（仅 frozen）

- 若同目录无 `config.yaml`：调用 `ConfigValidator.load_config(config_path)` 生成默认配置。
- 若同目录无 `cookies.json`：写入 `[]`。

### 3.3 启动方式（关键）

- **必须在主线程**执行 `uvicorn.run(...)`，否则 frozen 下会出现 `ModuleNotFoundError: No module named 'web'`。
- **必须先显式 `import web.app`**，再 `uvicorn.run(web.app.app, ...)`：
  - 显式 import 让 PyInstaller 分析时把 `web` 包及依赖打进 exe；
  - 直接传 `web.app.app` 对象，避免 uvicorn 运行时再解析字符串 `"web.app:app"`（PyInstaller 不会根据字符串收集模块）。

### 3.4 错误处理（仅 frozen）

- `sys.excepthook`：未捕获异常时打印 traceback，写入 `run_web_error.log`，并 `input("按回车键退出...")`。
- `main()` 内 try/except：捕获后调用 `_fatal()`，同样打印 + 写日志 + 等待回车。

---

## 4. 应用内 frozen 支持

### 4.1 `app/web/app.py`

- **静态资源根**  
  - frozen：`_web_base = sys._MEIPASS`  
  - 非 frozen：`_web_base = os.path.dirname(__file__)`  
  - `panel_dir`、`panel_assets_dir`、`panel_index_path`、`frontend_dir` 均基于 `_web_base` 计算。

- **自动打开浏览器**  
  在 FastAPI 的 `lifespan` 中（服务就绪、`yield` 之前），若 `sys.frozen` 为真，则启动一个 daemon 线程，延迟 1.5 秒后执行 `webbrowser.open("http://localhost:9527/panel/")`。

### 4.2 `app/server/api.py`

- **static 目录**  
  - frozen：`_server_base = os.path.join(sys._MEIPASS, "server")`，`static_dir = os.path.join(_server_base, "static")`。  
  - 非 frozen：`_server_base = os.path.dirname(__file__)`。  
- 仅当 `os.path.isdir(static_dir)` 为真时才 `app.mount("/static", StaticFiles(...))`，避免目录不存在时 Starlette 报错。

---

## 5. PyInstaller 配置：`run_web.spec`

### 5.1 入口与路径

- **入口脚本**：`app/run_web.py`
- **pathex**：`['app']`，保证从 app 目录解析 `web`、`core`、`server` 等包。

### 5.2 静态资源（datas）

打包时复制到临时目录 `_MEIPASS`，运行时通过 `sys._MEIPASS` 与上述路径逻辑配合使用：

| 源（项目内） | 目标（_MEIPASS 下） |
|--------------|---------------------|
| `app/web/frontend-v2/dist` | `frontend-v2/dist` |
| `app/web/frontend` | `frontend` |
| `app/server/static` | `server/static` |

### 5.3 hiddenimports

- uvicorn 相关：`uvicorn.logging`、`uvicorn.loops`、`uvicorn.loops.auto`、`uvicorn.protocols.*`、`uvicorn.lifespan`、`uvicorn.lifespan.on`。
- `core.config`（首次运行创建 config 时使用）。

### 5.4 输出与图标

- 单文件 exe：`--onefile`（spec 中 EXE 不含 `onefile=False` 即默认单文件）。
- 控制台：`console=True`，便于看日志与错误。
- 输出名：由 spec 的 `name=` 控制，当前为 `BiliBot_Web_V3_6.exe`。
- 自定义图标：spec 中 `icon='app/pmkix-xoym4-001.ico'`；输出文件名带版本号。

---

## 6. 打包与使用

### 6.1 环境

- Python 3.x，已安装 `app/requirements.txt` 依赖。
- 安装 PyInstaller：`pip install pyinstaller`（或直接使用项目根目录的 `build_web_exe.bat` 自动检查与安装）。

### 6.2 打包命令（项目根目录）

```bash
pyinstaller run_web.spec
```

或使用项目内置 Python：

```bash
.\python\python.exe -m PyInstaller run_web.spec
```

生成文件：`dist/BiliBot_Web_V3_6.exe`（名称在 spec 的 `name=` 中配置，含版本号）。

或在 **项目根目录** 直接双击 / 运行：

```bash
build_web_exe.bat
```

该脚本会：

- 自动检测（必要时尝试安装）PyInstaller；
- 调用内置 Python 执行 `pyinstaller run_web.spec`；
- 在 `dist/` 目录下生成 `BiliBot_Web_V3_6.exe`。

### 6.3 使用方式（最终给普通用户）

1. 将 exe 放到任意目录。
2. 首次运行会在同目录自动创建 `config.yaml`、`cookies.json`（若不存在）。
3. 双击 exe：启动服务并自动用系统默认浏览器打开 `http://localhost:9527/panel/`。
4. 关闭控制台窗口即停止服务。
5. 若报错：控制台会保留并提示，同时同目录生成 `run_web_error.log`。

---

## 7. 常见问题与对应方案

| 现象 | 原因 | 处理 |
|------|------|------|
| `No module named 'web'` | PyInstaller 不解析 uvicorn 的字符串 `"web.app:app"`，未打包 web 包；或在子线程中 import | 入口处显式 `import web.app`，并 `uvicorn.run(web.app.app, ...)`；uvicorn 必须在主线程运行 |
| exe 闪退 | 异常后控制台立即关闭 | 设置 `sys.excepthook` 与 try/except，打印 + 写 `run_web_error.log` + `input()` 等待回车 |
| `Directory '...\server\static' does not exist` | 未把 `server/static` 打进包，且代码用 `__file__` 在 frozen 下指向错误路径 | spec 的 datas 增加 `(app/server/static, server/static)`；`server/api.py` 在 frozen 下用 `sys._MEIPASS` 拼 `server/static`，且仅当目录存在时 mount |
| 配置/数据找不到 | 工作目录不是 exe 所在目录 | frozen 时 `os.chdir(os.path.dirname(sys.executable))` |

---

## 8. 不纳入本方案的内容

- 不把源码合并成“一个 .py”再打 exe（保持现有包结构）。
- 不打包 GUI 版（gui.py / main.py）；若需要可另做入口与 spec。
- Playwright 浏览器不打包进 exe，仍由用户在 config 中配置 `browser.path`。

---

*文档对应实现时间：2026-02，随项目迭代可再更新。*
