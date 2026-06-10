@echo off
chcp 65001 >nul
title 打包 Bilibili Bot v3.11 完整版

echo ============================================
echo   打包 Bilibili Bot v3.11 完整版
echo   包含 Python 运行环境
echo ============================================
echo.

REM 检查 PyInstaller
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未安装 PyInstaller
    echo 正在安装 PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] PyInstaller 安装失败
        pause
        exit /b 1
    )
)

REM 清理旧的构建文件
echo [*] 清理旧的构建文件...
if exist "build" rmdir /s /q build
if exist "dist\BiliBotLauncher_v3.11.exe" del /f /q "dist\BiliBotLauncher_v3.11.exe"
if exist "dist\BiliBot_v3.11_Portable" rmdir /s /q "dist\BiliBot_v3.11_Portable"

echo [*] 正在打包启动器...
echo.

REM 使用 launcher.spec 打包
python -m PyInstaller launcher.spec --clean

if errorlevel 1 (
    echo.
    echo [ERROR] 打包失败
    pause
    exit /b 1
)

echo.
echo [*] 正在创建便携版目录...
echo.

REM 创建便携版目录结构
mkdir "dist\BiliBot_v3.11_Portable"
mkdir "dist\BiliBot_v3.11_Portable\python"
mkdir "dist\BiliBot_v3.11_Portable\app"

REM 复制启动器
copy "dist\BiliBotLauncher_v3.11.exe" "dist\BiliBot_v3.11_Portable\"

REM 复制 Python 运行环境（如果存在）
if exist "python" (
    echo [*] 复制 Python 运行环境...
    xcopy /E /I /Y "python" "dist\BiliBot_v3.11_Portable\python"
) else (
    echo [WARNING] 未找到 python 目录，跳过 Python 环境复制
    echo [WARNING] 用户需要自行安装 Python 环境
)

REM 复制必要的配置文件
if exist "app\config.template.yaml" copy "app\config.template.yaml" "dist\BiliBot_v3.11_Portable\config.yaml"
if exist "app\license" xcopy /E /I /Y "app\license" "dist\BiliBot_v3.11_Portable\app\license"

REM 创建说明文件
echo 创建使用说明...
(
echo Bilibili Bot v3.11 便携版
echo ========================
echo.
echo 使用说明:
echo 1. 将 license.lic 文件放在本目录下
echo 2. 双击 BiliBotLauncher_v3.11.exe 启动
echo 3. 首次运行会自动验证 License
echo 4. 验证成功后点击"启动服务"
echo 5. 浏览器会自动打开 Web 面板
echo.
echo 目录结构:
echo - BiliBotLauncher_v3.11.exe  启动器
echo - python/                    Python 运行环境
echo - config.yaml                配置文件
echo - license.lic                License 文件（需自行放置）
echo - 用户数据/                  所有用户数据存储位置
echo.
echo 注意事项:
echo - 首次运行需要联网验证 License
echo - 确保防火墙允许程序访问网络
echo - 默认端口: 9527
echo - 所有配置和数据存储在"用户数据"文件夹
echo.
echo 版本: v3.11
echo 更新日期: 2026-03-27
echo.
echo 更新内容:
echo - 新增私信（DM）模式：搜索视频-爬评论区-筛选用户-自动发私信
echo - 新增评论区用户抓取器（CommentScraper），支持 Shadow DOM
echo - 新增两阶段用户筛选（正则 + AI 意向分析）
echo - 新增私信发送器（DmSender），支持多种输入框和发送方式
echo - 新增私信历史记录和去重机制
echo - 新增 Web 私信面板（DM Panel）及 API
echo - 版本号统一对齐至 v3.11
echo.
echo v3.10 更新内容:
echo - 修复浏览器资源泄漏问题（context 和 browser 正确关闭）
echo - 修复竞态条件导致的状态损坏和重复任务问题
echo - 修复裸 except 子句导致的异常吞噬问题
echo - 修复配置直接访问导致的 KeyError 崩溃
echo - 增强异常追踪日志（添加 traceback 详细信息）
echo - 提升系统稳定性和可靠性
echo - 优化资源管理和并发安全
echo.
echo v3.9 更新内容:
echo - 修复停止按钮无响应问题（1-2秒内快速停止）
echo - 修复浏览器关闭导致系统卡死问题
echo - 新增连续失败保护机制（5次失败自动停止）
echo - 新增浏览器连接检查（自动检测浏览器关闭）
echo - 优化停止信号检查点（多处检查确保快速响应）
echo - 优化等待机制（可中断等待，每秒检查停止信号）
echo - 用户数据目录优化（集中存储在"用户数据"文件夹）
) > "dist\BiliBot_v3.11_Portable\使用说明.txt"

echo.
echo ============================================
echo   打包完成！
echo ============================================
echo.
echo 输出目录: dist\BiliBot_v3.11_Portable\
echo.
echo 文件列表:
echo - BiliBotLauncher_v3.11.exe  (启动器)
echo - python\                    (Python 运行环境)
echo - config.yaml                (配置文件模板)
echo - 使用说明.txt               (使用说明)
echo.
echo 下一步:
echo 1. 将 license.lic 放入 BiliBot_v3.11_Portable 目录
echo 2. 打包整个 BiliBot_v3.11_Portable 目录分发给用户
echo 3. 用户解压后直接运行 BiliBotLauncher_v3.11.exe
echo.

pause
