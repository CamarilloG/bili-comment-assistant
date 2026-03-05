"""
本地测试启动脚本（自动安装依赖）
用于开发和测试
"""
import os
import sys
import subprocess

# 确保在正确的目录
if not os.path.exists('app'):
    print("[错误] 请在项目根目录运行此脚本")
    sys.exit(1)

print("=" * 60)
print("Bilibili Bot v3.10 - 本地测试启动")
print("=" * 60)
print()

# 检查并安装依赖
print("[1/3] 检查依赖库...")
required_modules = ['fastapi', 'uvicorn', 'playwright', 'pydantic', 'requests']
missing_modules = []

for module in required_modules:
    try:
        __import__(module)
        print(f"  OK {module}")
    except ImportError:
        print(f"  MISSING {module}")
        missing_modules.append(module)

if missing_modules:
    print()
    print(f"[提示] 缺少 {len(missing_modules)} 个依赖库")
    print("正在自动安装...")
    print()

    try:
        req_file = 'app/requirements.txt' if os.path.exists('app/requirements.txt') else 'requirements.txt'
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', req_file
        ])
        print()
        print("[OK] 依赖库安装完成")
    except subprocess.CalledProcessError as e:
        print()
        print(f"[错误] 依赖库安装失败: {e}")
        print()
        print("请手动安装:")
        print(f"  {sys.executable} -m pip install fastapi uvicorn")
        input("\n按回车键退出...")
        sys.exit(1)
else:
    print("[OK] All dependencies installed")

print()

# 添加 app 目录到路径
app_dir = os.path.join(os.getcwd(), 'app')
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# 检查配置文件
print("[2/3] 检查配置文件...")
config_path = os.path.join('用户数据', 'config.yaml')
if not os.path.exists(config_path):
    print("[INFO] Config file not found, creating default config")
    try:
        from core.slot import ensure_slot_dir, get_config_path
        from core.config import ConfigValidator
        ensure_slot_dir("0")
        ConfigValidator.load_config(get_config_path("0"))
        print("[OK] Default config created")
    except Exception as e:
        print(f"[WARNING] Failed to create config: {e}")
else:
    print("[OK] Config file exists")

print()

# 启动 Web 服务
print("[3/3] 启动 Web 服务...")
print()
print("=" * 60)
print("服务地址: http://localhost:9527/panel/")
print()
print("按 Ctrl+C 停止服务")
print("=" * 60)
print()

try:
    import web.app
    import uvicorn

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {
            "uvicorn": {"level": "CRITICAL"},
            "uvicorn.access": {"level": "CRITICAL"},
        },
    }

    # Python 3.13 兼容性：使用 asyncio.WindowsSelectorEventLoopPolicy
    import asyncio
    import sys
    if sys.platform == 'win32' and sys.version_info >= (3, 13):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    uvicorn.run(
        web.app.app,
        host="0.0.0.0",
        port=9527,
        access_log=False,
        log_config=log_config,
    )

except KeyboardInterrupt:
    print()
    print("=" * 60)
    print("服务已停止")
    print("=" * 60)
except Exception as e:
    print()
    print("=" * 60)
    print(f"启动失败: {e}")
    print("=" * 60)
    import traceback
    traceback.print_exc()
    input("\n按回车键退出...")
    sys.exit(1)
