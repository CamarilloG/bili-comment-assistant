#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
抖音自动化GUI v2.0 启动脚本
单步操作模式 - 性能优化版
"""

import sys
from pathlib import Path

# 添加项目路径
app_dir = Path(__file__).parent / "app"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

from douyin.gui_v2 import main

if __name__ == "__main__":
    main()
