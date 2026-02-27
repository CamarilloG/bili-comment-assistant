# Web 版单文件 exe 打包说明

完整实现说明与常见问题见�?*[docs/Web版单文件exe打包实现说明.md](docs/Web版单文件exe打包实现说明.md)**�?
## 环境

- Python 3.x，已安装 `app/requirements.txt` 中的依赖
- 安装 PyInstaller：`pip install pyinstaller`

## 打包

�?*项目根目�?*执行�?
```bash
pyinstaller run_web.spec
```

生成的可执行文件�?`dist/B站评论助手_Web_V3.exe`�?
## 使用

1. �?`B站评论助手_Web_V3.exe` 放到任意目录
2. **首次运行**时，exe 会在同目录自动创�?`config.yaml`（默认配置）�?`cookies.json`（空列表）；若已存在则不会覆�?3. 双击 exe：会启动 Web 服务�?*自动用系统默认浏览器打开** `http://localhost:9527/panel/` 控制台页�?4. 关闭控制台窗口即停止服务

## 说明

- 浏览器需�?config 中配�?`browser.path`（Playwright 要求），与未打包时一�?- 若杀毒软件误报，可添加信任或使用签名
