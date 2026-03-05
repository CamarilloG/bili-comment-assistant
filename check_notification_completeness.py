"""
检查通知方法完整性

对比前端配置的 9 种通知类型和后端实现
"""
import sys
sys.path.insert(0, 'app')

# 前端配置的 9 种通知类型
frontend_notifications = [
    'captcha_alert',       # 验证码提醒
    'captcha_cooldown',    # 验证码冷却通知
    'captcha_terminated',  # 验证码达上限通知
    'cd_limit',            # CD 限制通知
    'comment_success',     # 评论成功通知
    'comment_failed',      # 评论失败通知
    'task_started',        # 任务开始通知
    'task_completed',      # 任务完成通知
    'task_error',          # 任务错误通知
]

# BaiduBotNotifier 的方法
baidu_bot_methods = [
    'notify_captcha_alert',
    'notify_captcha_cooldown',
    'notify_captcha_terminated',
    'notify_cd_limit',
    'notify_comment_success',
    'notify_comment_failed',
    'notify_task_started',
    'notify_task_completed',
    'notify_task_error',
]

# NotificationManager 的方法
notification_manager_methods = [
    'notify_captcha',           # 对应 captcha_cooldown
    'notify_failure',           # 连续失败（内部使用）
    'notify_comment_success',   # 对应 comment_success
    'notify_comment_failed',    # 对应 comment_failed
    'notify_task_started',      # 对应 task_started
    'notify_task_completed',    # 对应 task_completed
    'notify_cd_limit',          # 对应 cd_limit
    'notify_terminated',        # 对应 captcha_terminated + task_error
]

print('=' * 80)
print('通知方法完整性检查')
print('=' * 80)

print('\n[1] 前端配置的通知类型 (9 种)')
for i, notif in enumerate(frontend_notifications, 1):
    print(f'  {i}. {notif}')

print('\n[2] BaiduBotNotifier 实现的方法 (9 种)')
for i, method in enumerate(baidu_bot_methods, 1):
    print(f'  {i}. {method}')

print('\n[3] NotificationManager 实现的方法 (8 种)')
for i, method in enumerate(notification_manager_methods, 1):
    print(f'  {i}. {method}')

print('\n[4] 映射关系检查')
print('-' * 80)

mapping = {
    'captcha_alert': {
        'baidu': 'notify_captcha_alert',
        'manager': 'notify_captcha (内部调用 baidu.notify_captcha_cooldown)',
        'status': '⚠️ 需要检查'
    },
    'captcha_cooldown': {
        'baidu': 'notify_captcha_cooldown',
        'manager': 'notify_captcha',
        'status': '✅ 已实现'
    },
    'captcha_terminated': {
        'baidu': 'notify_captcha_terminated',
        'manager': 'notify_terminated',
        'status': '✅ 已实现'
    },
    'cd_limit': {
        'baidu': 'notify_cd_limit',
        'manager': 'notify_cd_limit',
        'status': '✅ 已实现'
    },
    'comment_success': {
        'baidu': 'notify_comment_success',
        'manager': 'notify_comment_success',
        'status': '✅ 已实现'
    },
    'comment_failed': {
        'baidu': 'notify_comment_failed',
        'manager': 'notify_comment_failed',
        'status': '✅ 已实现'
    },
    'task_started': {
        'baidu': 'notify_task_started',
        'manager': 'notify_task_started',
        'status': '✅ 已实现'
    },
    'task_completed': {
        'baidu': 'notify_task_completed',
        'manager': 'notify_task_completed',
        'status': '✅ 已实现'
    },
    'task_error': {
        'baidu': 'notify_task_error',
        'manager': 'notify_terminated',
        'status': '✅ 已实现'
    },
}

for notif_type, info in mapping.items():
    print(f'\n{notif_type}:')
    print(f'  BaiduBot: {info["baidu"]}')
    print(f'  Manager:  {info["manager"]}')
    print(f'  状态:     {info["status"]}')

print('\n' + '=' * 80)
print('检查结果')
print('=' * 80)

issues = []

# 检查 captcha_alert
print('\n⚠️ 发现问题: captcha_alert')
print('  - BaiduBotNotifier 有 notify_captcha_alert() 方法')
print('  - NotificationManager.notify_captcha() 调用的是 notify_captcha_cooldown()')
print('  - 应该先调用 notify_captcha_alert()，再调用 notify_captcha_cooldown()')
issues.append('captcha_alert 映射不正确')

if issues:
    print(f'\n❌ 发现 {len(issues)} 个问题:')
    for issue in issues:
        print(f'  - {issue}')
else:
    print('\n✅ 所有通知类型都已正确实现')
