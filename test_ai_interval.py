"""
测试 AI 调用间隔功能
"""
import time
from core.ai_provider import AIProvider

# 测试配置
test_config = {
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "your-api-key-here",  # 需要替换为真实的 API Key
    "api_type": "openai"
}

print("=" * 60)
print("AI 调用间隔测试")
print("=" * 60)

# 测试 1: 无间隔
print("\n[测试 1] 无调用间隔（request_interval=0）")
provider1 = AIProvider(
    test_config,
    timeout=30,
    max_retries=1,
    request_interval=0,
    retry_delay_base=2.0
)

start = time.time()
for i in range(3):
    print(f"\n第 {i+1} 次调用...")
    result = provider1.chat(
        system_prompt="你是一个助手",
        user_prompt="说一句话",
        temperature=0.7,
        max_tokens=50
    )
    print(f"结果: {result[:50] if result else 'None'}...")
elapsed = time.time() - start
print(f"\n总耗时: {elapsed:.1f}s")

# 测试 2: 3秒间隔
print("\n" + "=" * 60)
print("[测试 2] 3秒调用间隔（request_interval=3.0）")
provider2 = AIProvider(
    test_config,
    timeout=30,
    max_retries=1,
    request_interval=3.0,
    retry_delay_base=2.0
)

start = time.time()
for i in range(3):
    print(f"\n第 {i+1} 次调用...")
    result = provider2.chat(
        system_prompt="你是一个助手",
        user_prompt="说一句话",
        temperature=0.7,
        max_tokens=50
    )
    print(f"结果: {result[:50] if result else 'None'}...")
elapsed = time.time() - start
print(f"\n总耗时: {elapsed:.1f}s")
print(f"预期耗时: 约 {3 * 2 + 3}s（3次调用 + 2次间隔）")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
