"""测试通知系统"""
import time
from core.notification_manager import get_notification_manager

def test_notifications():
    """测试各种类型的通知"""
    mgr = get_notification_manager()

    print("测试 1: 验证码通知")
    mgr.notify_captcha("0", 1, 30)
    time.sleep(2)

    print("测试 2: 连续失败通知（需要3次）")
    mgr.notify_failure("1", "评论被拒绝")
    time.sleep(1)
    mgr.notify_failure("1", "网络超时")
    time.sleep(1)
    mgr.notify_failure("1", "账号异常")  # 第3次，应该触发通知
    time.sleep(2)

    print("测试 3: 任务终止通知")
    mgr.notify_terminated("0", "验证码次数达到上限")
    time.sleep(2)

    print("测试 4: 普通通知")
    mgr.send_notification(
        title="测试通知",
        message="这是一条普通信息",
        notification_type="info",
        slot_id="0",
        show_system=False
    )
    time.sleep(2)

    print("测试 5: 成功后重置失败计数")
    mgr.reset_failure_count("1")
    mgr.notify_failure("1", "新的失败")  # 应该从1开始计数

    print("\n所有测试完成！")
    print("请检查：")
    print("1. 前端是否显示了吐司通知")
    print("2. Windows 系统通知是否弹出（仅验证码、连续失败、任务终止）")

if __name__ == "__main__":
    test_notifications()
