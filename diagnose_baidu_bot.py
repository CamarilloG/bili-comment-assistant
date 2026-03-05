"""百度机器人诊断工具"""
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

print('=' * 80)
print('百度机器人配置诊断')
print('=' * 80)

# 1. 检查配置
print('\n[1] 配置检查')
print(f'  Enabled: {baidu_config.get("enabled")}')
print(f'  API URL: {baidu_config.get("api_url")}')
print(f'  Access Token: {baidu_config.get("access_token")[:10]}...{baidu_config.get("access_token")[-5:]}')
print(f'  Group ID: {baidu_config.get("group_id")}')

# 2. 检查网络连接
print('\n[2] 网络连接检查')
api_host = baidu_config['api_url'].split('/')[2]
print(f'  API Host: {api_host}')

try:
    import socket
    ip = socket.gethostbyname(api_host)
    print(f'  DNS 解析: ✓ {ip}')
except Exception as e:
    print(f'  DNS 解析: ✗ {e}')

# 3. 测试 API 连接
print('\n[3] API 连接测试')
url = f"{baidu_config['api_url']}?access_token={baidu_config['access_token']}"

# 简单的 ping 测试
try:
    response = requests.get(baidu_config['api_url'], timeout=5)
    print(f'  GET 请求: {response.status_code}')
except Exception as e:
    print(f'  GET 请求: ✗ {e}')

# 4. 测试消息发送
print('\n[4] 消息发送测试')
payload = {
    'message': {
        'header': {
            'toid': [int(baidu_config['group_id'])]
        },
        'body': [
            {
                'type': 'TEXT',
                'content': '测试消息'
            }
        ]
    }
}

try:
    response = requests.post(
        url,
        json=payload,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    print(f'  Status Code: {response.status_code}')
    print(f'  Response Headers: {dict(response.headers)}')
    print(f'  Response Body: {response.text}')

    if response.status_code == 200:
        print('\n✓ 消息发送成功！')
    elif response.status_code == 502:
        print('\n✗ 502 Bad Gateway')
        print('  可能原因:')
        print('  1. 不在百度内网环境')
        print('  2. 需要 VPN 连接')
        print('  3. API 地址不正确')
        print('  4. Access Token 无效')
    elif response.status_code == 401:
        print('\n✗ 401 Unauthorized')
        print('  Access Token 无效或过期')
    elif response.status_code == 400:
        print('\n✗ 400 Bad Request')
        print('  请求格式错误')
    else:
        print(f'\n✗ 未知错误: {response.status_code}')

except requests.exceptions.Timeout:
    print('\n✗ 请求超时')
    print('  可能原因: 网络连接问题或 API 服务不可达')
except requests.exceptions.ConnectionError as e:
    print(f'\n✗ 连接错误: {e}')
    print('  可能原因: 无法连接到 API 服务器')
except Exception as e:
    print(f'\n✗ 未知错误: {e}')

print('\n' + '=' * 80)
print('诊断完成')
print('=' * 80)
