# 抖音自动化（独立目录）

本目录包含**全部**抖音相关逻辑，与 B 站 `app/core`、`app/modules` 等分离，不混用。

## 目录结构

```
app/douyin/
├── README.md       # 本说明 + 登录抓取与整合流程
├── __init__.py     # 导出 DouyinSelectors, DouyinSearchManager, run_search_flow, DouyinModule
├── selectors.py    # 页面选择器（搜索框、按钮、登录等）
├── auth.py         # 登录态：Cookie 保存/加载/注入（用户数据/douyin_cookies.json）
├── search.py       # 首页、登录检查、搜索框输入、点击搜索、结果解析、翻页
├── flow.py         # 整合入口：run_search_flow(page, keyword, max_count)
└── module.py       # IModule 实现，供 app 注册为 "douyin" capability
```

## 整合流程（一步到位）

1. **登录信息保存** → `auth.save_douyin_cookies()` / `save_douyin_cookies_from_header()`
2. **注入 Cookie** → `auth.inject_douyin_cookies_to_page(page)`（每次操作前自动）
3. **打开首页** → `DouyinSearchManager.open_homepage()`
4. **确认登录态** → `DouyinSearchManager.check_login_status()`
5. **定位输入框** → `[data-e2e='searchbar-input']`
6. **输入关键词** → `type(keyword, delay=80)`
7. **点击搜索** → `[data-e2e='searchbar-button']`
8. **返回结果** → `get_current_page_videos()`

一行调用：`from douyin import run_search_flow; videos = run_search_flow(page, keyword="关键词", max_count=20)`

## 登录态抓取与保存

### 抓取步骤（Chrome MCP + 网络监听）

1. 用 MCP `user-chrome-devtools` 的 `new_page` 打开 `https://www.douyin.com/`。
2. 点击「登录」→ 手机扫码登录。
3. 登录成功后，`list_network_requests` 找已登录请求（如 `aweme/v1/web/user/settings`），用 `get_network_request(reqid)` 取 **Request Headers** 里的 `cookie`。
4. 保存：调用 `douyin.auth.save_douyin_cookies_from_header(cookie_header)`，或按下方格式写 **用户数据/douyin_cookies.json**。

### 本地文件格式（用户数据/douyin_cookies.json）

```json
{
  "cookies": [
    { "name": "sessionid", "value": "xxx", "domain": ".douyin.com", "path": "/" },
    { "name": "sid_guard", "value": "xxx", "domain": ".douyin.com", "path": "/" }
  ],
  "updated_at": "2026-03-02T12:00:00"
}
```

至少保留 `sessionid`、`sid_guard`、`sid_tt`、`uid_tt`。未写 `domain`/`path` 时自动补为 `.douyin.com`、`/`。

## 与主应用的衔接

- 主应用仅在两处与抖音目录交互：
  - `app/web/app.py`：`from douyin import DouyinModule` 并 `registry.register("douyin", DouyinModule())`。
  - 调度器为 douyin 传入 `page` 时，会调用 `DouyinModule.set_page(page)`。
- 其余 B 站逻辑不引用本目录，本目录仅引用 `modules.base`、`utils.logger`、`core.slot`（auth 用到的路径）。

## 安全

- `douyin_cookies.json` 为登录凭证，勿提交版本库、勿泄露。已通过 `.gitignore` 忽略。
