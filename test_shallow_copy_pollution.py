"""
浅拷贝配置污染问题深度分析

这个测试演示了 ai_filter_module.py 和 ai_gen_module.py 中
使用 dict() 浅拷贝导致的配置污染问题。
"""

import copy
import sys
import io

# 设置 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def demonstrate_shallow_copy_problem():
    """演示浅拷贝导致的配置污染"""

    print("=" * 80)
    print("浅拷贝配置污染问题演示")
    print("=" * 80)

    # 模拟原始配置（类似 self._config）
    original_config = {
        "ai": {
            "enabled": False,
            "model_id": "gpt-4",
            "filter": {
                "enabled": False,
                "criteria": "original criteria"
            },
            "comment": {
                "enabled": False,
                "user_intent": "original intent",
                "style": "casual",
                "max_length": 100
            }
        },
        "behavior": {
            "min_delay": 5,
            "max_delay": 15
        }
    }

    print("\n【原始配置】")
    print(f"original_config['ai']['filter']['criteria'] = {original_config['ai']['filter']['criteria']}")
    print(f"original_config['ai']['comment']['user_intent'] = {original_config['ai']['comment']['user_intent']}")
    print(f"original_config['ai']['enabled'] = {original_config['ai']['enabled']}")

    # ============================================================
    # 问题代码 1: ai_filter_module.py 的 _build_manager() 方法
    # ============================================================
    print("\n" + "=" * 80)
    print("【问题 1】ai_filter_module.py 的浅拷贝问题")
    print("=" * 80)

    # 模拟 ai_filter_module.py:60-67 的代码
    cfg = dict(original_config)  # ❌ 浅拷贝
    ai_section = dict(cfg.get("ai", {}))  # ❌ 浅拷贝
    ai_section["enabled"] = True
    filter_section = dict(ai_section.get("filter", {}))  # ❌ 浅拷贝
    filter_section["enabled"] = True
    filter_section["criteria"] = "MODIFIED BY FILTER MODULE"  # 修改
    ai_section["filter"] = filter_section
    cfg["ai"] = ai_section

    print("\n执行 ai_filter_module._build_manager() 后:")
    print(f"cfg['ai']['filter']['criteria'] = {cfg['ai']['filter']['criteria']}")
    print(f"original_config['ai']['filter']['criteria'] = {original_config['ai']['filter']['criteria']}")

    if original_config['ai']['filter']['criteria'] == "MODIFIED BY FILTER MODULE":
        print("[X] 配置污染！原始配置被修改了！")
    else:
        print("[OK] 原始配置未被污染")

    # ============================================================
    # 问题代码 2: ai_gen_module.py 的 _build_manager() 方法
    # ============================================================
    print("\n" + "=" * 80)
    print("【问题 2】ai_gen_module.py 的浅拷贝问题")
    print("=" * 80)

    # 重置配置
    original_config['ai']['comment']['user_intent'] = "original intent"

    # 模拟 ai_gen_module.py:63-76 的代码
    params = {
        "persona": "MODIFIED BY GEN MODULE",
        "style": "hardcore",
        "max_length": 200
    }

    cfg2 = dict(original_config)  # ❌ 浅拷贝
    ai_section2 = dict(cfg2.get("ai", {}))  # ❌ 浅拷贝
    ai_section2["enabled"] = True
    comment_section = dict(ai_section2.get("comment", {}))  # ❌ 浅拷贝
    comment_section["enabled"] = True
    if params.get("persona"):
        comment_section["user_intent"] = params["persona"]
    if params.get("style"):
        comment_section["style"] = params["style"]
    if params.get("max_length"):
        comment_section["max_length"] = params["max_length"]
    ai_section2["comment"] = comment_section
    cfg2["ai"] = ai_section2

    print("\n执行 ai_gen_module._build_manager() 后:")
    print(f"cfg2['ai']['comment']['user_intent'] = {cfg2['ai']['comment']['user_intent']}")
    print(f"original_config['ai']['comment']['user_intent'] = {original_config['ai']['comment']['user_intent']}")

    if original_config['ai']['comment']['user_intent'] == "MODIFIED BY GEN MODULE":
        print("[X] 配置污染！原始配置被修改了！")
    else:
        print("[OK] 原始配置未被污染")

    # ============================================================
    # 深层污染分析
    # ============================================================
    print("\n" + "=" * 80)
    print("【深层污染分析】为什么会发生污染？")
    print("=" * 80)

    # 重置配置
    test_config = {
        "ai": {
            "nested": {
                "value": "original"
            }
        }
    }

    # 浅拷贝
    shallow = dict(test_config)

    print("\n1. 浅拷贝后，顶层字典是新对象：")
    print(f"   test_config is shallow: {test_config is shallow}")
    print(f"   id(test_config) = {id(test_config)}")
    print(f"   id(shallow) = {id(shallow)}")

    print("\n2. 但嵌套字典仍然共享引用：")
    print(f"   test_config['ai'] is shallow['ai']: {test_config['ai'] is shallow['ai']}")
    print(f"   id(test_config['ai']) = {id(test_config['ai'])}")
    print(f"   id(shallow['ai']) = {id(shallow['ai'])}")

    print("\n3. 修改嵌套字典会影响原始配置：")
    shallow['ai']['nested']['value'] = "POLLUTED"
    print(f"   shallow['ai']['nested']['value'] = {shallow['ai']['nested']['value']}")
    print(f"   test_config['ai']['nested']['value'] = {test_config['ai']['nested']['value']}")
    print("   [X] 原始配置被污染！")

    # ============================================================
    # 正确的解决方案
    # ============================================================
    print("\n" + "=" * 80)
    print("【正确的解决方案】使用 copy.deepcopy()")
    print("=" * 80)

    # 重置配置
    correct_config = {
        "ai": {
            "nested": {
                "value": "original"
            }
        }
    }

    # 深拷贝
    deep = copy.deepcopy(correct_config)

    print("\n1. 深拷贝后，所有层级都是新对象：")
    print(f"   correct_config is deep: {correct_config is deep}")
    print(f"   correct_config['ai'] is deep['ai']: {correct_config['ai'] is deep['ai']}")
    print(f"   correct_config['ai']['nested'] is deep['ai']['nested']: {correct_config['ai']['nested'] is deep['ai']['nested']}")

    print("\n2. 修改深拷贝不会影响原始配置：")
    deep['ai']['nested']['value'] = "MODIFIED"
    print(f"   deep['ai']['nested']['value'] = {deep['ai']['nested']['value']}")
    print(f"   correct_config['ai']['nested']['value'] = {correct_config['ai']['nested']['value']}")
    print("   [OK] 原始配置未被污染！")


def demonstrate_real_world_impact():
    """演示实际场景中的影响"""

    print("\n" + "=" * 80)
    print("【实际场景影响分析】")
    print("=" * 80)

    # 模拟多实例场景
    slot_0_config = {
        "ai": {
            "filter": {"criteria": "Slot 0 criteria"},
            "comment": {"user_intent": "Slot 0 intent"}
        }
    }

    print("\n场景：两个 slot 实例同时运行")
    print(f"Slot 0 初始配置: filter.criteria = '{slot_0_config['ai']['filter']['criteria']}'")

    # Slot 0 调用 ai_filter_module
    print("\n1. Slot 0 调用 ai_filter_module._build_manager()")
    cfg_slot0 = dict(slot_0_config)
    ai_section_slot0 = dict(cfg_slot0.get("ai", {}))
    filter_section_slot0 = dict(ai_section_slot0.get("filter", {}))
    filter_section_slot0["criteria"] = "Slot 0 MODIFIED"
    ai_section_slot0["filter"] = filter_section_slot0
    cfg_slot0["ai"] = ai_section_slot0

    print(f"   cfg_slot0['ai']['filter']['criteria'] = '{cfg_slot0['ai']['filter']['criteria']}'")
    print(f"   slot_0_config['ai']['filter']['criteria'] = '{slot_0_config['ai']['filter']['criteria']}'")

    # 如果发生污染
    if slot_0_config['ai']['filter']['criteria'] == "Slot 0 MODIFIED":
        print("\n[X] 污染发生！")
        print("   后果：")
        print("   - Slot 0 的原始配置被修改")
        print("   - 如果 Slot 0 再次调用 _build_manager()，会使用被污染的配置")
        print("   - 多次调用会累积污染，导致配置越来越混乱")
        print("   - 不同模块之间的配置会相互干扰")

    # ============================================================
    # 并发场景下的污染
    # ============================================================
    print("\n" + "=" * 80)
    print("【并发场景下的污染风险】")
    print("=" * 80)

    shared_config = {
        "ai": {
            "filter": {"criteria": "shared"},
            "comment": {"user_intent": "shared"}
        }
    }

    print("\n场景：多个线程同时访问共享配置")
    print("Thread 1: ai_filter_module 修改 filter.criteria")
    print("Thread 2: ai_gen_module 修改 comment.user_intent")
    print("Thread 3: 读取配置")

    # 模拟 Thread 1
    cfg_t1 = dict(shared_config)
    ai_t1 = dict(cfg_t1.get("ai", {}))
    filter_t1 = dict(ai_t1.get("filter", {}))
    filter_t1["criteria"] = "Thread 1 modified"
    ai_t1["filter"] = filter_t1
    cfg_t1["ai"] = ai_t1

    # 模拟 Thread 2
    cfg_t2 = dict(shared_config)
    ai_t2 = dict(cfg_t2.get("ai", {}))
    comment_t2 = dict(ai_t2.get("comment", {}))
    comment_t2["user_intent"] = "Thread 2 modified"
    ai_t2["comment"] = comment_t2
    cfg_t2["ai"] = ai_t2

    print(f"\nThread 3 读取到的配置:")
    print(f"  filter.criteria = '{shared_config['ai']['filter']['criteria']}'")
    print(f"  comment.user_intent = '{shared_config['ai']['comment']['user_intent']}'")

    if (shared_config['ai']['filter']['criteria'] == "Thread 1 modified" or
        shared_config['ai']['comment']['user_intent'] == "Thread 2 modified"):
        print("\n[X] 竞态条件！配置被并发修改污染！")
        print("   后果：")
        print("   - 不同线程看到的配置不一致")
        print("   - 难以调试和重现的 bug")
        print("   - 可能导致 AI 生成结果错误")


def analyze_memory_references():
    """分析内存引用关系"""

    print("\n" + "=" * 80)
    print("【内存引用关系分析】")
    print("=" * 80)

    original = {
        "level1": {
            "level2": {
                "level3": {
                    "value": "deep nested"
                }
            }
        }
    }

    shallow = dict(original)
    deep = copy.deepcopy(original)

    print("\n浅拷贝的引用关系：")
    print(f"Level 0 (顶层): original is shallow = {original is shallow}")
    print(f"Level 1: original['level1'] is shallow['level1'] = {original['level1'] is shallow['level1']}")
    print(f"Level 2: original['level1']['level2'] is shallow['level1']['level2'] = {original['level1']['level2'] is shallow['level1']['level2']}")
    print(f"Level 3: original['level1']['level2']['level3'] is shallow['level1']['level2']['level3'] = {original['level1']['level2']['level3'] is shallow['level1']['level2']['level3']}")

    print("\n深拷贝的引用关系：")
    print(f"Level 0 (顶层): original is deep = {original is deep}")
    print(f"Level 1: original['level1'] is deep['level1'] = {original['level1'] is deep['level1']}")
    print(f"Level 2: original['level1']['level2'] is deep['level1']['level2'] = {original['level1']['level2'] is deep['level1']['level2']}")
    print(f"Level 3: original['level1']['level2']['level3'] is deep['level1']['level2']['level3'] = {original['level1']['level2']['level3'] is deep['level1']['level2']['level3']}")

    print("\n结论：")
    print("- 浅拷贝：只有顶层是新对象，所有嵌套对象都共享引用")
    print("- 深拷贝：所有层级都是新对象，完全独立")


if __name__ == "__main__":
    demonstrate_shallow_copy_problem()
    demonstrate_real_world_impact()
    analyze_memory_references()

    print("\n" + "=" * 80)
    print("【总结】")
    print("=" * 80)
    print("""
浅拷贝配置污染的三个关键问题：

1. 【配置污染】
   - 使用 dict() 浅拷贝嵌套字典时，嵌套对象仍然共享引用
   - 修改拷贝会影响原始配置
   - 多次调用会累积污染

2. 【并发风险】
   - 多线程同时修改共享配置会导致竞态条件
   - 不同实例之间的配置会相互干扰
   - 难以调试和重现

3. 【影响范围】
   - ai_filter_module.py: 修改 filter.criteria
   - ai_gen_module.py: 修改 comment.user_intent, style, max_length
   - ai_center/model_router.py: 修改路由配置

修复方案：
将所有 dict() 替换为 copy.deepcopy()

修复位置：
- app/modules/ai_filter_module.py:60-67
- app/modules/ai_gen_module.py:63-76
- app/ai_center/model_router.py:178
""")
