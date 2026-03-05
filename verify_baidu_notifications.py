"""
百度机器人通知验证脚本

验证所有通知功能是否正常工作
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'app')

from core.slot import get_config_path
from core.config import ConfigValidator
from core.notification_manager import NotificationManager

print('=' * 80)
print('百度机器人通知验证')
print('=' * 80)

# 1. 加载配置
print('\n[1] 加载配置')
config = ConfigValidator.load_config(get_config_path('0'))
baidu_config = config.get('bots', {}).get('baidu', {})

print(f'  Enabled: {baidu_config.get("enabled")}')
print(f'  API URL: {baidu_config.get("api_url")}')
print(f'  Group ID: {baidu_config.get("group_id")}')
print(f'  Notifications: {list(baidu_config.get("notifications", {}).keys())}')

# 2. 初始化通知管理器
print('\n[2] 初始化通知管理器')
mgr = NotificationManager()
mgr.update_config(config)

print(f'  Baidu bot initialized: {mgr._baidu_bot is not None}')
if mgr._baidu_bot:
    print(f'  Baidu bot enabled: {mgr._baidu_bot.enabled}')
    print(f'  API URL: {mgr._baidu_bot.api_url}')
    print(f'  Group ID: {mgr._baidu_bot.group_id}')

# 3. 测试通知方法
print('\n[3] 测试通知方法')

test_methods = [
    ('notify_task_started', lambda: mgr.notify_task_started('0', '评论任务', 10)),
    ('notify_comment_success', lambda: mgr.notify_comment_success('0', '测试视频', '测试评论')),
    ('notify_comment_failed', lambda: mgr.notify_comment_failed('0', '测试视频', '测试失败原因')),
    ('notify_captcha', lambda: mgr.notify_captcha('0', 1, 30)),
    ('notify_cd_limit', lambda: mgr.notify_cd_limit('0', 3)),
    ('notify_task_completed', lambda: mgr.notify_task_completed('0', '评论任务', 8, 10)),
]

for method_name, method_call in test_methods:
    try:
        print(f'\n  测试 {method_name}...')
        method_call()
        print(f'    ✓ 方法调用成功')
    except Exception as e:
        print(f'    ✗ 方法调用失败: {e}')

# 4. 发送测试消息
print('\n[4] 发送测试消息')
if mgr._baidu_bot and mgr._baidu_bot.enabled:
    try:
        result = mgr._baidu_bot.send_test_message()
        if result:
            print('  ✓ 测试消息发送成功！请检查群组消息')
        else:
            print('  ✗ 测试消息发送失败（可能是网络问题或 502 错误）')
    except Exception as e:
        print(f'  ✗ 发送测试消息异常: {e}')
else:
    print('  ✗ 百度机器人未启用或未初始化')

print('\n' + '=' * 80)
print('验证完成')
print('=' * 80)
print('\n说明:')
print('- 如果看到 502 错误，说明不在百度内网环境')
print('- 所有方法调用成功表示代码集成正确')
print('- 实际推送需要在百度内网环境验证')
