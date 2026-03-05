import sys
sys.path.insert(0, 'app')

from core.slot import get_config_path
from core.config import ConfigValidator

config = ConfigValidator.load_config(get_config_path('0'))
baidu_config = config.get('bots', {}).get('baidu', {})

print('=' * 80)
print('百度机器人配置检查')
print('=' * 80)

print(f'启用状态: {baidu_config.get("enabled")}')
print(f'API地址: {baidu_config.get("api_url")}')
print(f'群组ID: {baidu_config.get("group_id")}')
print(f'Access Token 长度: {len(baidu_config.get("access_token", ""))}')

print('\n通知类型配置:')
notifications = baidu_config.get("notifications", {})
for key, value in notifications.items():
    status = "✅启用" if value else "❌禁用"
    print(f'  {key}: {status}')

print('=' * 80)