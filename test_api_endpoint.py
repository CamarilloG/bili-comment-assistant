"""
测试 API 端点是否可达
"""
import requests
import time

print("=" * 60)
print("测试 API 端点")
print("=" * 60)
print()

# 测试服务是否运行
print("[1/3] 测试服务连接...")
try:
    response = requests.get("http://localhost:9527/api/config?slot=0", timeout=5)
    print(f"✓ 服务连接成功 - 状态码: {response.status_code}")
except Exception as e:
    print(f"✗ 无法连接到服务: {e}")
    print("  请确保服务正在运行")
    exit(1)

print()

# 测试任务状态端点
print("[2/3] 测试任务状态端点...")
try:
    response = requests.get("http://localhost:9527/api/task/comment/status?slot=0", timeout=5)
    print(f"✓ 状态端点可达 - 状态码: {response.status_code}")
    print(f"  响应: {response.json()}")
except Exception as e:
    print(f"✗ 状态端点失败: {e}")

print()

# 测试启动端点（不实际启动，只测试可达性）
print("[3/3] 测试启动端点...")
try:
    # 先检查是否已在运行
    status_response = requests.get("http://localhost:9527/api/task/comment/status?slot=0", timeout=5)
    status_data = status_response.json()

    if status_data.get("running"):
        print("⚠ 任务正在运行，跳过启动测试")
    else:
        print("  发送启动请求...")
        response = requests.post(
            "http://localhost:9527/api/task/comment/start?slot=0",
            json={"mode": "comment"},
            timeout=10
        )
        print(f"✓ 启动端点可达 - 状态码: {response.status_code}")
        print(f"  响应: {response.json()}")

        # 等待 2 秒后检查状态
        time.sleep(2)
        status_response = requests.get("http://localhost:9527/api/task/comment/status?slot=0", timeout=5)
        status_data = status_response.json()
        print(f"  2秒后状态: running={status_data.get('running')}, status={status_data.get('status')}")

except Exception as e:
    print(f"✗ 启动端点失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("测试完成")
print("=" * 60)
