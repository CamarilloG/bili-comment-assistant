# Bilibili Bot v3.7 打包说明

## 已完成的改进

### 1. 版本更新
- 版本号更新到 v3.7
- 文件名包含版本号：`BiliBotLauncher_v3.7.exe`
- 添加完整的版本信息（右键属性可查看）

### 2. License 验证整合
- ✅ 不再弹出独立验证窗口
- ✅ 验证界面集成到主启动器
- ✅ 自动查找 license.lic 文件
- ✅ 支持手动选择 License 文件

### 3. 前端路由修复
- ✅ 修复打包后前端 404 问题
- ✅ 正确配置 `sys._MEIPASS` 路径
- ✅ 前端文件正确打包到 exe 中

### 4. 集成运行环境
- ✅ 打包包含所有 Python 依赖
- ✅ 无需客户端预装 Python
- ✅ 真正的"开箱即用"

### 5. 图标和界面
- ✅ 添加自定义图标
- ✅ 无控制台窗口（纯 GUI）
- ✅ 专业的界面设计

## 便携版目录结构

```
BiliBot_v3.7_Portable/
├── BiliBotLauncher_v3.7.exe  (67MB - 包含所有依赖)
├── python/                    (Python 运行环境 - 可选)
├── config.yaml                (配置文件模板)
├── license.lic                (License 文件 - 需要放置)
└── 使用说明.txt
```

## 打包命令

### 快速打包（仅启动器）
```bash
python -m PyInstaller launcher.spec --clean
```

### 完整打包（包含 Python 环境）
```bash
build_portable.bat
```

## 分发说明

### 给客户的文件
1. 整个 `BiliBot_v3.7_Portable` 文件夹
2. 或者只分发 `BiliBotLauncher_v3.7.exe` + `license.lic`

### 客户使用步骤
1. 解压到任意目录
2. 将 `license.lic` 放在 exe 同目录
3. 双击 `BiliBotLauncher_v3.7.exe`
4. 自动验证 License
5. 点击"启动服务"
6. 浏览器自动打开 Web 面板

## 系统要求
- Windows 10/11 (64位)
- 无需预装 Python
- 至少 500MB 磁盘空间
- 至少 2GB 内存

## 技术细节

### 打包配置
- 使用 PyInstaller 6.18.0
- 单文件模式（onefile）
- 包含所有依赖库
- 前端文件打包路径：`web/frontend-v2/dist`

### 关键修复
1. **前端路径**：`sys._MEIPASS/web/frontend-v2/dist`
2. **License 验证**：集成到主界面，不再独立窗口
3. **版本信息**：使用 `version_info.txt`
4. **图标**：使用 `.ico` 格式

## 文件大小
- 启动器 exe：约 67MB
- 完整便携版（含 Python）：约 200-300MB

## 注意事项
1. 首次运行需要联网验证 License
2. 防火墙可能需要允许程序访问网络
3. 默认端口 9527，确保端口未被占用
4. 建议使用 Chrome/Edge 浏览器访问 Web 面板

## 更新日志 v3.7
- [新增] License 验证集成到主界面
- [新增] 添加图标和版本信息
- [修复] 前端路由 404 问题
- [优化] 启动流程更流畅
- [优化] 文件名包含版本号
