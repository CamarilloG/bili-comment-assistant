"""演示百度机器人完整功能"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'app')

from core.baidu_bot import BaiduBotNotifier

# 创建百度机器人配置（这里我们复用现有的配置）
from core.slot import get_config_path
from core.config import ConfigValidator

config = ConfigValidator.load_config(get_config_path('0'))
baidu_config = config.get('bots', {}).get('baidu', {})

print('=' * 80)
print('百度机器人功能演示')
print('=' * 80)

# 创建通知器
print(f'创建百度机器人通知器...')
notifier = BaiduBotNotifier(baidu_config)
print(f'启用状态: {"✅已启用" if notifier.enabled else "❌未启用"}')
print(f'群组ID: {notifier.group_id}')
print(f'通知类型配置: {list(notifier.notifications.keys())}')

# 发送不同种类的通知演示
if notifier.enabled:
    print('\n' + '=' * 80)
    print('演示不同通知类型')
    print('=' * 80)
    
    print('\n1. 任务开始通知...')
    notifier.notify_task_started("评论任务", 10, slot_id=1)
    
    print('\n2. 验证码提醒...')
    notifier.notify_captcha_alert("comment", "视频: BV123456789", slot_id=1)
    
    print('\n3. 验证码冷却通知...')
    notifier.notify_captcha_cooldown(1, 30, 10, slot_id=1)
    
    print('\n4. 评论成功通知（如果启用）...')
    notifier.notify_comment_success("测试视频标题", "这是一个测试评论", slot_id=1)
    
    print('\n5. 评论失败通知...')
    notifier.notify_comment_failed("测试视频标题", "连接超时", slot_id=1)
    
    print('\n6. CD限制通知...')
    notifier.notify_cd_limit(3, slot_id=1)
    
    print('\n7. 任务完成通知...')
    notifier.notify_task_completed("评论任务", 8, 10, slot_id=1)
    
    print('\n8. 任务错误通知...')
    notifier.notify_task_error("评论任务", "网络连接失败，请检查网络", slot_id=1)
    
    print('\n9. 验证码达上限通知...')
    notifier.notify_captcha_terminated(3, 3, slot_id=1)

    print('\n' + '=' * 80)
    print('演示完成！请检查百度如流群组中的消息。')
    print('=' * 80)
else:
    print('\n❌ 百度机器人未启用，请检查配置！')

print('\n' + '=' * 80)
print('如何在代码中使用百度机器人：')
print('=' * 80)

print('''
# 从配置中读取百度机器人配置
from app.core.baidu_bot import BaiduBotNotifier
from app.core.slot import get_config_path
from app.core.config import ConfigValidator

# 加载配置
config = ConfigValidator.load_config(get_config_path('0'))
baidu_config = config.get('bots', {}).get('baidu', {})

# 创建通知器
notifier = BaiduBotNotifier(baidu_config)

# 发送不同通知
if notifier.enabled:
    # 1. 任务开始通知
    notifier.notify_task_started("评论任务", 10, slot_id=1)
    
    # 2. 验证码提醒
    notifier.notify_captcha_alert("comment", "视频: BV123456789", slot_id=1)
    
    # 3. 验证码冷却通知
    notifier.notify_captcha_cooldown(1, 30, 10, slot_id=1)
    
    # 4. CD限制通知
    notifier.notify_cd_limit(3, slot_id=1)
    
    # 5. 任务完成通知
    notifier.notify_task_completed("评论任务", 8, 10, slot_id=1)
''')