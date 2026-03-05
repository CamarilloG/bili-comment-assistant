"""
v3.10 最终验证脚本
快速验证所有修复是否正确
"""
import sys
import os
import subprocess

# 设置 UTF-8 输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def run_test(test_file, description):
    """运行测试脚本"""
    print(f"\n{'=' * 60}")
    print(f"运行测试: {description}")
    print('=' * 60)

    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30
        )

        print(result.stdout)

        if result.returncode == 0:
            return True
        else:
            print(f"❌ 测试失败，返回码: {result.returncode}")
            if result.stderr:
                print(f"错误输出:\n{result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ 测试超时")
        return False
    except Exception as e:
        print(f"❌ 运行测试时出错: {e}")
        return False


def check_syntax(file_path, description):
    """检查 Python 文件语法"""
    print(f"\n检查语法: {description}")
    print('-' * 60)

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', file_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=10
        )

        if result.returncode == 0:
            print(f"✅ {description} 语法正确")
            return True
        else:
            print(f"❌ {description} 语法错误")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ 检查语法时出错: {e}")
        return False


def main():
    """运行所有验证"""
    print("=" * 60)
    print("v3.10 最终验证")
    print("=" * 60)

    results = []

    # 1. 语法检查
    print("\n" + "=" * 60)
    print("第一步: 语法检查")
    print("=" * 60)

    syntax_checks = [
        ('app/launcher_gui.py', 'GUI 启动器'),
        ('app/web/app.py', 'Web 应用'),
        ('app/web/routers/bot_api.py', '百度机器人 API'),
        ('app/main.py', '主程序'),
    ]

    for file_path, desc in syntax_checks:
        results.append((f"语法检查: {desc}", check_syntax(file_path, desc)))

    # 2. 运行测试
    print("\n" + "=" * 60)
    print("第二步: 运行测试")
    print("=" * 60)

    tests = [
        ('test_gui_fixes.py', 'GUI 启动器修复测试'),
        ('test_baidu_bot_fix.py', '百度机器人修复测试'),
    ]

    for test_file, desc in tests:
        if os.path.exists(test_file):
            results.append((desc, run_test(test_file, desc)))
        else:
            print(f"\n⚠️  测试文件不存在: {test_file}")
            results.append((desc, False))

    # 3. 检查前端构建
    print("\n" + "=" * 60)
    print("第三步: 检查前端构建")
    print("=" * 60)

    dist_path = 'app/web/frontend-v2/dist'
    if os.path.exists(dist_path):
        index_path = os.path.join(dist_path, 'index.html')
        assets_path = os.path.join(dist_path, 'assets')

        if os.path.exists(index_path) and os.path.exists(assets_path):
            print("✅ 前端构建完成")
            results.append(("前端构建", True))
        else:
            print("❌ 前端构建不完整")
            results.append(("前端构建", False))
    else:
        print("❌ 前端未构建")
        results.append(("前端构建", False))

    # 4. 汇总结果
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print()
    print(f"总计: {passed} 通过, {failed} 失败")

    if failed == 0:
        print("\n" + "=" * 60)
        print("🎉 所有验证通过！v3.10 准备就绪！")
        print("=" * 60)
        print()
        print("✅ 核心 BUG 修复完成")
        print("✅ GUI 启动器修复完成")
        print("✅ 百度机器人测试修复完成")
        print("✅ 前端重新构建完成")
        print()
        print("可以开始打包:")
        print("  - build_launcher.bat (正式版)")
        print("  - build_launcher_debug.bat (调试版)")
        print("  - build_portable.bat (完整便携版)")
        print()
        return 0
    else:
        print("\n" + "=" * 60)
        print("⚠️ 部分验证失败")
        print("=" * 60)
        print()
        print("请检查失败的项目并修复")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
