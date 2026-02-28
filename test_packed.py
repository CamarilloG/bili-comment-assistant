"""
测试打包后的 exe 是否包含前端文件
"""
import sys
import os

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    print(f"运行在打包环境，_MEIPASS: {base_path}")
else:
    base_path = os.path.dirname(__file__)
    print(f"运行在开发环境，base_path: {base_path}")

# 检查前端文件
frontend_path = os.path.join(base_path, "web", "frontend-v2", "dist")
print(f"\n前端路径: {frontend_path}")
print(f"前端目录存在: {os.path.exists(frontend_path)}")

if os.path.exists(frontend_path):
    print(f"\n前端目录内容:")
    for item in os.listdir(frontend_path):
        item_path = os.path.join(frontend_path, item)
        if os.path.isdir(item_path):
            print(f"  [DIR]  {item}")
        else:
            size = os.path.getsize(item_path)
            print(f"  [FILE] {item} ({size} bytes)")

    # 检查 assets 目录
    assets_path = os.path.join(frontend_path, "assets")
    if os.path.exists(assets_path):
        print(f"\nassets 目录内容:")
        for item in os.listdir(assets_path)[:10]:  # 只显示前10个
            print(f"  - {item}")
else:
    print("前端目录不存在！")

# 检查 index.html
index_path = os.path.join(frontend_path, "index.html")
print(f"\nindex.html 存在: {os.path.exists(index_path)}")

input("\n按回车键退出...")
