# Web 面板常见问题与修复记录

本文档整理 Web 控制面板（前端 + FastAPI 后端）在开发与使用中遇到的报错及最终修复方式，便于排查与复现。

---

## 1. 问题一览

| 现象 | 根因概要 | 详见章节 |
|------|----------|----------|
| Chrome 控制台请求 `/.well-known/...` 报 404 | 无对应路由 | 2.1 |
| 页面白屏，控制台报「Expected a JavaScript module but got text/html」 | 静态 JS 被当成 SPA 返回了 index.html | 2.2 |
| 访问 `/panel/ai` 或刷新后 404 | SPA 前端路由未回退到 index.html | 2.3 |
| 保存配置后刷新，配置丢失 / 未写入文件 | 配置路径不一致 + 浅合并覆盖 | 2.4、2.5 |
| AI 设置页已保存内容不显示 | 进页时 config 未就绪且 watch 未覆盖 | 2.6 |
| 选择「AI 评论」仍走普通评论 | 仅根据 `ai.enabled` 创建 provider | 2.7 |
| 吐司提示不明显、看不到 | 右上角小条不显眼 | 2.8 |
| 保存后弹窗不出现 | 前端未重新构建，仍用旧 bundle | 2.9 |
| 控制台运行日志不显示（一直「等待日志输出...」） | 旧版 frontend 挂载在 `/` 拦截了 `/ws/logs` | 2.10 |

---

## 2. 各问题与修复

### 2.1 Chrome DevTools 请求 404

**现象**  
控制台出现：`GET /.well-known/appspecific/com.chrome.devtools.json 404`。

**原因**  
Chrome 打开开发者工具时会自动请求该 URL，后端无对应路由。

**修复**  
在 `app/web/app.py` 增加路由，返回空 JSON 即可：

```python
@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_well_known() -> Dict[str, Any]:
    return {}
```

---

### 2.2 静态 JS 被当成 HTML 返回（MIME 错误）

**现象**  
控制台报错：`Failed to load module script: Expected a JavaScript module but the server responded with a MIME type of "text/html"`，页面白屏或无法加载。

**原因**  
存在兜底路由 `@app.get("/panel/{full_path:path}")` 且注册在 `app.mount("/panel", StaticFiles(...))` **之前**。请求 `/panel/assets/index-xxx.js` 时被该路由命中，统一返回了 `index.html`。

**修复**  
- 不要用「先于 mount 的」泛路径路由把 `/panel/*` 全包掉。  
- 若需 SPA 回退，应先挂载静态资源（见 2.3），再对非静态路径做回退。

---

### 2.3 前端路由（如 /panel/ai）404

**现象**  
直接访问或刷新 `/panel/ai` 返回 404，或保存后跳转到该路径时 404。

**原因**  
Starlette 的 `StaticFiles(..., html=True)` 只会在「路径对应磁盘上的目录」时回退到 index.html；像 `ai` 这种不存在的路径会直接 404，不会回退。

**修复**  
在 `app/web/app.py` 中：

1. **先挂载静态资源**：`app.mount("/panel/assets", StaticFiles(directory=panel_assets_dir))`，保证 `/panel/assets/*.js`、`*.css` 由静态服务正确返回。
2. **再为 SPA 做回退**：  
   - `GET /panel` → 返回 `index.html`  
   - `GET /panel/{full_path:path}` → 返回 `index.html`（`/panel/assets/*` 已被上面 mount 处理，不会进这里）。

这样 `/panel/ai` 等前端路由都会落到回退路由，由前端路由接管。

---

### 2.4 配置保存不到文件（路径不一致）

**现象**  
在面板里点击保存，接口 200，但刷新后配置没了；或日志里写的是「已保存」，实际打开的是另一个 `config.yaml`。

**原因**  
读写配置使用相对路径 `"config.yaml"`，依赖进程当前工作目录。用 `start.bat` 在 `app` 下启动时写的是 `app/config.yaml`；若从别处启动（如项目根、IDE），可能写到别的目录，读到的又是另一份文件。

**修复**  
- 在 `app/core/config.py` 中定义基于「app 根目录」的绝对路径：  
  `_CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))`，  
  `DEFAULT_CONFIG_PATH = os.path.join(_CONFIG_DIR, "config.yaml")`。  
- `load_config()` / `save_config()` 默认使用 `DEFAULT_CONFIG_PATH`；  
- `app/web/routers/config_api.py` 读写也统一用 `DEFAULT_CONFIG_PATH`。  
- 保存时建议原子写入：先写 `config.yaml.tmp`，`flush` + `fsync` 后再 `os.replace(tmp, path)`，避免写一半或未落盘。

---

### 2.5 配置保存后整段被清空（浅合并）

**现象**  
在 AI 设置里填好 API Key 等并保存成功，但点「开始任务」后报「请填写 API Key」；打开 `config.yaml` 发现 `ai` 里只剩 `comment.enabled` 等少量字段，其余被清空。

**原因**  
控制台在启动任务前会发一次：`configStore.save({ ai: { comment: { enabled: true } } })`。后端用 `existing.update(incoming)` 做**浅合并**，整块 `existing["ai"]` 被替换成 `{ comment: { enabled: true } }`，`api_key`、`base_url` 等全部丢失，再写回文件就把配置清空了。

**修复**  
在 `config_api.py` 中对待合并的 `body.config` 做**深合并**，例如实现 `_deep_merge(base, incoming)`：对嵌套对象递归合并，只更新 `incoming` 里出现的键，不整块替换。合并后再 `validate_and_fill_defaults` 并 `save_config`。

---

### 2.6 AI 设置页内容加载不出

**现象**  
进入 AI 设置页后，已保存的配置经常不显示，需要切到别的页再切回来，或刷新一两次才出现。

**原因**  
- 只在 `onMounted` 时若已有 `config?.ai` 才填表；若此时全局 `config` 尚未从接口返回，就不会填表。  
- 虽然后面用 `watch(..., { once: true })` 等 config 到来，但未设 `immediate: true`，且未在「无 config 时」主动拉取，存在时序差时容易漏掉一次。

**修复**  
在 AI 设置页（如 `AISettings.vue`）：

- `onMounted` 时若 `!configStore.config`，先执行一次 `configStore.load()`，保证进页就有一次拉取。  
- 使用 `watch(() => configStore.config?.ai, (ai) => { if (ai) loadFromConfig(ai) }, { immediate: true })`：  
  - `immediate: true`：若进入时已有 `config.ai` 会立刻填表；  
  - config 之后才到时，watch 会再触发一次填表。

---

### 2.7 选「AI 评论」仍用普通评论

**现象**  
在控制台选择「AI 评论」并开始任务，实际发出的仍是模板评论。

**原因**  
创建 AI 客户端（provider）的条件原先为「仅当 `ai.enabled === true`」。用户若只勾了「智能评论」（`ai.comment.enabled`）而没勾顶部的「启用 AI 功能」（`ai.enabled`），则 provider 为 null，`is_comment_enabled()` 为 false，仍走模板评论。

**修复**  
在 `app/core/ai_manager.py` 中，创建 provider 的条件改为：**有 `api_key` 且（智能评论或智能筛选任一开启）** 即创建，不再依赖 `ai.enabled`。若后续移除「整体开关」，则逻辑只根据 `ai.comment.enabled` / `ai.filter` + `api_key` 判断即可。

---

### 2.8 保存结果提示不明显（吐司看不到）

**现象**  
保存后希望有明确提示，但右上角吐司不显眼，用户不知道是否保存成功。

**修复**  
改为**居中弹窗**：  
- 新增 `stores/alertModal.js`（如 `show(message, type)`、`success`、`error`、`close`）。  
- 新增 `components/AlertModal.vue`：半透明遮罩 + 居中白底框 + 文案 +「确定」按钮；成功/失败用不同样式（如按钮颜色）。  
- 各设置页保存成功/失败时调用 `alertModal.success(...)` / `alertModal.error(...)`，不再使用吐司。

---

### 2.9 保存后弹窗不出现

**现象**  
已改成弹窗提醒，但点击保存后没有任何弹窗。

**原因**  
前端代码已改，但**未重新构建**；浏览器加载的仍是旧的 `dist` 里的 JS/CSS，不包含 AlertModal 与 alertModal 的调用。

**修复**  
在 `app/web/frontend-v2` 下执行 `npm run build`（或 `npx vite build`）重新构建前端。构建完成后**强制刷新**浏览器（如 Ctrl+F5）或重新打开面板地址，再试保存即可看到弹窗。

---

### 2.10 控制台运行日志不显示

**现象**  
控制台「运行日志」区域一直显示「等待日志输出...」，养号或评论任务在运行但页面无任何日志输出。

**原因**  
当存在 `app/web/frontend` 目录时，后端将旧版前端通过 `app.mount("/", StaticFiles(...))` 挂载在根路径 **`/`**。Starlette 会优先用该挂载处理所有路径，导致 **`/ws/logs`** 的 WebSocket 请求被当作静态文件处理，无法到达 `log_api`；后端 `broadcast_log` 时该 slot 订阅者数为 0，日志无法推送到前端。

**修复**  
在 `app/web/app.py` 中，将旧版前端的挂载路径由 **`"/"`** 改为 **`"/app"`**：

```python
# 旧版 frontend 挂到 /app，避免 mount("/") 拦截 /ws、/api
if os.path.isdir(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")
```

修改后重启后端；若使用打包前端，需在 `app/web/frontend-v2` 下执行 `npm run build` 并强刷页面。访问地址仍为 `http://localhost:9527/panel/`。

---

## 3. 小结

| 类型 | 建议 |
|------|------|
| **路由与静态** | Panel 用「先 mount /panel/assets，再 /panel 与 /panel/{path} 回退 index.html」；避免泛路径回退优先于静态。 |
| **配置读写** | 统一用基于 app 根目录的绝对路径；保存用深合并 + 原子写入。 |
| **前端状态** | 进设置页若无 config 可主动 load；用 watch + immediate 保证「已有或后到」都能填表。 |
| **前端发布** | 改完 Vue/逻辑后务必重新 build，并强刷或重开页面再验证。 |

---

*文档基于实际报错与修复整理，若后续有同类问题可先查本表与对应章节。*
