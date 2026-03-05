# 抖音网站自动化（独立目录，与 B 站 app/core、app/modules 等无混用）
# 整合流程：登录信息保存 → 自动打开首页 → 确认登录态 → 定位输入框 → 输入关键词 → 点击搜索。

from douyin.selectors import DouyinSelectors
from douyin.search import DouyinSearchManager
from douyin.flow import run_search_flow
from douyin.module import DouyinModule

__all__ = ["DouyinSelectors", "DouyinSearchManager", "run_search_flow", "DouyinModule"]
