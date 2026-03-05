"""测试百度机器人修复（检查日志输出）"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'app')

from core.slot import get_config_path
from core.config import ConfigValidator
from core.baidu_bot import BaiduBotNotifier

# 加载配置
config = ConfigValidator.load_config(get_config_path('0'))
baidu_config = config.get('bots', {}).get('baidu', {})

print('=' * 80)
print('百度机器人修复验证测试')
print('=' * 80)
print(f'API URL: {baidu_config.get("api_url")}')
print(f'Group ID: {baidu_config.get("group_id")}')
print(f'Enabled: {baidu_config.get("enabled")}')
print('=' * 80)

# 创建通知器
notifier = BaiduBotNotifier(baidu_config)

# 发送测试消息
print('\n[*] 发送测试消息...')
success = notifier.send_test_message()

print(f'\n发送结果: {"✅ 成功" if success else "❌ 失败"}')
print('=' * 80)

# 检查日志
print('\n测试完成！请检查百度如流群组(11917896)中是否收到测试消息。')
print('如果收到消息，说明百度机器人完全正常工作。')