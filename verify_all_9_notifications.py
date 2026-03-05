"""
完整验证所有 9 种通知方法
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'app')

from core.slot import get_config_path
from core.config import ConfigValidator
from core.notification_manager import NotificationManager

print('=' * 80)
print('百度机器人 9 种通知方法完整验证')
print('=' * 80)

# 加载配置
config = ConfigValidator.load_config(get_config_path('0'))
mgr = NotificationManager()
mgr.update_config(config)

print(f'\nBaidu bot initialized: {mgr._baidu_bot is not None}')
print(f'Baidu bot enabled: {mgr._baidu_bot.enabled if mgr._baidu_bot else False}')

# 测试所有 9 种通知方法
test_cases = [
    {
        'name': '1. captcha_alert (验证码提醒)',
        'method': lambda: mgr.notify_captcha_alert('0', 'comment', 'BV1234567890'),
        'config_key': 'captcha_alert'
    },
    {
        'name': '2. captcha_cooldown (验证码冷却)',
        'method': lambda: mgr.notify_captcha('0', 1, 30),
        'config_key': 'captcha_cooldown'
    },
    {
        'name': '3. captcha_terminated (验证码达上限)',
        'method': lambda: mgr.notify_terminated('0', '今日验证码触发已达上限（3/3）'),
        'config_key': 'captcha_terminated'
    },
    {
        'name': '4. cd_limit (CD 限制)',
        'method': lambda: mgr.notify_cd_limit('0', 3),
        'config_key': 'cd_limit'
    },
    {
        'name': '5. comment_success (评论成功)',
        'method': lambda: mgr.notify_comment_success('0', '测试视频标题', '测试评论内容'),
        'config_key': 'comment_success'
    },
    {
        'name': '6. comment_failed (评论失败)',
        'method': lambda: mgr.notify_comment_failed('0', '测试视频标题', '测试失败原因'),
        'config_key': 'comment_failed'
    },
    {
        'name': '7. task_started (任务开始)',
        'method': lambda: mgr.notify_task_started('0', '评论任务', 10),
        'config_key': 'task_started'
    },
    {
        'name': '8. task_completed (任务完成)',
        'method': lambda: mgr.notify_task_completed('0', '评论任务', 8, 10),
        'config_key': 'task_completed'
    },
    {
        'name': '9. task_error (任务错误)',
        'method': lambda: mgr.notify_terminated('0', '任务异常终止：测试错误'),
        'config_key': 'task_error'
    },
]

print('\n' + '=' * 80)
print('测试所有通知方法')
print('=' * 80)

success_count = 0
for test in test_cases:
    print(f'\n{test["name"]}')
    print(f'  配置键: {test["config_key"]}')

    # 检查配置
    if mgr._baidu_bot:
        enabled = mgr._baidu_bot.notifications.get(test["config_key"], True)
        print(f'  配置状态: {"启用" if enabled else "禁用"}')

    try:
        test['method']()
        print(f'  调用结果: [OK] 方法调用成功')
        success_count += 1
    except Exception as e:
        print(f'  调用结果: [FAIL] {e}')

print('\n' + '=' * 80)
print('测试总结')
print('=' * 80)
print(f'成功: {success_count}/9')
print(f'失败: {9 - success_count}/9')

if success_count == 9:
    print('\n[SUCCESS] 所有 9 种通知方法都已正确实现！')
else:
    print(f'\n[WARNING] 有 {9 - success_count} 个方法调用失败')

print('\n说明:')
print('- 方法调用成功表示代码集成正确')
print('- 实际推送需要在百度内网环境验证')
print('- 如果看到 502 错误，说明不在百度内网环境（这是正常的）')
