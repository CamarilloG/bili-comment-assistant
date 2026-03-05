#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
抖音自动化GUI启动脚本
v2.5 集成版 - 使用已集成新组件的 gui.py
"""

import sys
from pathlib import Path

# 添加项目路径
app_dir = Path(__file__).parent / "app"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

# 导入并启动GUI
from douyin.gui import main

if __name__ == "__main__":
    main()
