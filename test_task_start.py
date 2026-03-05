"""
测试任务启动 API
直接调用后端 API 测试任务启动
"""
import sys
import os
import requests
import time

print("=" * 60)
print("任务启动 API 测试")
print("=" * 60)
print()

# 测试服务是否运行
print("[1/4] 测试服务连接...")
try:
    response = requests.get("http://localhost:9527/api/config?slot=0", timeout=5)
    if response.status_code == 200:
        print("✓ 服务连接成功")
    else:
        print(f"✗ 服务返回错误: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"✗ 无法连接到服务: {e}")
    print("  请确保服务正在运行: python start_dev.py")
    sys.exit(1)

print()

# 测试登录状态
print("[2/4] 测试登录状态...")
try:
    response = requests.get("http://localhost:9527/api/auth/status?slot=0", timeout=5)
    data = response.json()
    if data.get("logged_in"):
        print("✓ 已登录")
    else:
        print("✗ 未登录")
        print("  请先在 Web 面板扫码登录")
        sys.exit(1)
except Exception as e:
    print(f"✗ 检查登录状态失败: {e}")
    sys.exit(1)

print()

# 测试任务状态
print("[3/4] 测试任务状态...")
try:
    response = requests.get("http://localhost:9527/api/task/comment/status?slot=0", timeout=5)
    data = response.json()
    if data.get("running"):
        print("⚠ 任务正在运行")
        print("  请先停止任务")
        sys.exit(1)
    else:
        print("✓ 任务未运行，可以启动")
except Exception as e:
    print(f"✗ 检查任务状态失败: {e}")
    sys.exit(1)

print()

# 启动任务
print("[4/4] 启动任务...")
print("  正在发送启动请求...")

try:
    response = requests.post(
        "http://localhost:9527/api/task/comment/start?slot=0",
        json={"mode": "comment"},
        timeout=10
    )

    print(f"  响应状态码: {response.status_code}")
    print(f"  响应内容: {response.text}")

    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "ok":
            print("✓ 任务启动请求成功")
            print()
            print("  等待 3 秒后检查任务状态...")
            time.sleep(3)

            # 检查任务是否真的启动了
            response = requests.get("http://localhost:9527/api/task/comment/status?slot=0", timeout=5)
            data = response.json()

            if data.get("running"):
                print("✓ 任务正在运行")
                print(f"  状态: {data.get('status')}")
                print(f"  视频数: {data.get('video_count')}")
            else:
                print("✗ 任务未运行")
                print(f"  状态: {data.get('status')}")
        else:
            print(f"✗ 任务启动失败: {data.get('message')}")
    else:
        print(f"✗ 请求失败: {response.status_code}")
        print(f"  {response.text}")

except requests.exceptions.Timeout:
    print("✗ 请求超时")
    print("  这可能是因为:")
    print("  1. 浏览器启动卡住")
    print("  2. 登录检查卡住")
    print("  3. 配置加载失败")
    print()
    print("  请查看日志: 用户数据/logs/bili_bot_2026-03-04.log")

except Exception as e:
    print(f"✗ 启动失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("测试完成")
print("=" * 60)
print()
print("请查看日志文件获取详细信息:")
print("  用户数据/logs/bili_bot_2026-03-04.log")
print()
print("查看日志命令:")
print("  tail -f 用户数据/logs/bili_bot_2026-03-04.log")
print()
