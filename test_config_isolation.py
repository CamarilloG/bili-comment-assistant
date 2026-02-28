"""测试多实例配置隔离"""
import sys
import os

# 设置控制台编码
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except:
        pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from core.config import ConfigValidator
from core.slot import get_config_path, ensure_slot_dir
import copy

def test_config_isolation():
    """测试配置隔离性"""
    print("=" * 60)
    print("测试 1: DEFAULT_CONFIG 深拷贝隔离")
    print("=" * 60)

    # 获取两次配置
    config1 = ConfigValidator.validate_and_fill_defaults({}, strict=False)
    config2 = ConfigValidator.validate_and_fill_defaults({}, strict=False)

    # 修改 config1 的嵌套字典
    config1["ai"]["comment"]["enabled"] = False
    config1["ai"]["comment"]["user_intent"] = "测试实例1"

    # 检查 config2 是否被影响
    print(f"config1 ai.comment.enabled: {config1['ai']['comment']['enabled']}")
    print(f"config2 ai.comment.enabled: {config2['ai']['comment']['enabled']}")
    print(f"config1 ai.comment.user_intent: {config1['ai']['comment']['user_intent']}")
    print(f"config2 ai.comment.user_intent: {config2['ai']['comment']['user_intent']}")

    if config2["ai"]["comment"]["enabled"] == False:
        print("❌ 失败：config2 被 config1 污染了！")
        return False
    else:
        print("✅ 成功：config1 和 config2 完全隔离")

    print()
    print("=" * 60)
    print("测试 2: DEFAULT_CONFIG 本身是否被污染")
    print("=" * 60)

    default_enabled = ConfigValidator.DEFAULT_CONFIG["ai"]["comment"]["enabled"]
    default_intent = ConfigValidator.DEFAULT_CONFIG["ai"]["comment"]["user_intent"]

    print(f"DEFAULT_CONFIG ai.comment.enabled: {default_enabled}")
    print(f"DEFAULT_CONFIG ai.comment.user_intent: {default_intent}")

    if default_enabled == False or default_intent == "测试实例1":
        print("❌ 失败：DEFAULT_CONFIG 被污染了！")
        return False
    else:
        print("✅ 成功：DEFAULT_CONFIG 未被污染")

    print()
    print("=" * 60)
    print("测试 3: 多实例配置文件隔离")
    print("=" * 60)

    # 确保实例目录存在
    ensure_slot_dir("0")
    ensure_slot_dir("1")
    ensure_slot_dir("2")

    # 加载实例 0 的配置
    config0_path = get_config_path("0")
    config0 = ConfigValidator.load_config(config0_path)
    config0["search"]["keywords"] = ["实例0关键词"]
    config0["comment"]["texts"] = ["实例0评论"]
    ConfigValidator.save_config(config0, config0_path)

    # 加载实例 1 的配置
    config1_path = get_config_path("1")
    config1 = ConfigValidator.load_config(config1_path)
    config1["search"]["keywords"] = ["实例1关键词"]
    config1["comment"]["texts"] = ["实例1评论"]
    ConfigValidator.save_config(config1, config1_path)

    # 加载实例 2 的配置
    config2_path = get_config_path("2")
    config2 = ConfigValidator.load_config(config2_path)
    config2["search"]["keywords"] = ["实例2关键词"]
    config2["comment"]["texts"] = ["实例2评论"]
    ConfigValidator.save_config(config2, config2_path)

    # 重新读取验证
    config0_reload = ConfigValidator.load_config(config0_path)
    config1_reload = ConfigValidator.load_config(config1_path)
    config2_reload = ConfigValidator.load_config(config2_path)

    print(f"实例 0 关键词: {config0_reload['search']['keywords']}")
    print(f"实例 1 关键词: {config1_reload['search']['keywords']}")
    print(f"实例 2 关键词: {config2_reload['search']['keywords']}")

    print(f"实例 0 评论: {config0_reload['comment']['texts']}")
    print(f"实例 1 评论: {config1_reload['comment']['texts']}")
    print(f"实例 2 评论: {config2_reload['comment']['texts']}")

    # 检查是否隔离
    if (config0_reload['search']['keywords'] == ["实例0关键词"] and
        config1_reload['search']['keywords'] == ["实例1关键词"] and
        config2_reload['search']['keywords'] == ["实例2关键词"]):
        print("✅ 成功：多实例配置完全隔离")
        return True
    else:
        print("❌ 失败：多实例配置被混淆了！")
        return False

if __name__ == "__main__":
    try:
        success = test_config_isolation()
        print()
        print("=" * 60)
        if success:
            print("🎉 所有测试通过！配置隔离正常工作")
        else:
            print("⚠️ 测试失败！配置隔离存在问题")
        print("=" * 60)
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
