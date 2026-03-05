"""测试百度机器人 API 调用"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'app')

from core.slot import get_config_path
from core.config import ConfigValidator
import requests

# 加载配置
config = ConfigValidator.load_config(get_config_path('0'))
baidu_config = config.get('bots', {}).get('baidu', {})

# 构建请求
url = f"{baidu_config['api_url']}?access_token={baidu_config['access_token']}"
payload = {
    'message': {
        'header': {
            'toid': [int(baidu_config['group_id'])]
        },
        'body': [
            {
                'type': 'TEXT',
                'content': '🤖 测试消息\n\n这是来自 Bilibili Bot 的测试通知\n\n如果收到此消息，说明配置成功！'
            }
        ]
    }
}

print('=' * 80)
print('百度机器人测试')
print('=' * 80)
print(f'URL: {url}')
print(f'Group ID: {baidu_config["group_id"]}')
print(f'Payload: {payload}')
print('=' * 80)

try:
    response = requests.post(
        url,
        json=payload,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    print(f'Status Code: {response.status_code}')
    print(f'Response: {response.text}')

    if response.status_code == 200:
        print('\n✓ 消息发送成功！')
    else:
        print(f'\n✗ 消息发送失败: {response.status_code}')

except Exception as e:
    print(f'Error: {e}')
