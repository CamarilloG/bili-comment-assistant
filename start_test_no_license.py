"""
本地测试启动脚本（跳过 License 验证）
用于开发和测试
"""
import os
import sys

# 确保在正确的目录
if not os.path.exists('app'):
    print("[错误] 请在项目根目录运行此脚本")
    sys.exit(1)

# 添加 app 目录到路径
app_dir = os.path.join(os.getcwd(), 'app')
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

print("=" * 60)
print("Bilibili Bot v3.10 - 本地测试启动（跳过 License）")
print("=" * 60)
print()

# 检查配置文件
config_path = os.path.join('用户数据', 'config.yaml')
if not os.path.exists(config_path):
    print("[提示] 配置文件不存在，将自动创建默认配置")
    try:
        from core.slot import ensure_slot_dir, get_config_path
        from core.config import ConfigValidator
        ensure_slot_dir("0")
        ConfigValidator.load_config(get_config_path("0"))
        print("[OK] 已创建默认配置")
    except Exception as e:
        print(f"[警告] 创建配置失败: {e}")
    print()

# 启动 Web 服务
print("正在启动 Web 服务...")
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
