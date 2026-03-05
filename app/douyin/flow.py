# 抖音自动化整合流程：登录态注入 → 打开首页 → 确认登录 → 定位输入框 → 输入关键词 → 点击搜索 → 返回结果。
# 与 B 站业务无耦合。

from __future__ import annotations

from typing import TYPE_CHECKING

from utils.logger import get_logger

if TYPE_CHECKING:
    from playwright.sync_api import Page

logger = get_logger()


def run_search_flow(
    page: "Page",
    keyword: str,
    max_count: int = 20,
    inject_cookie: bool = False,  # 改为False，避免重复注入
    captcha_callback=None,  # 新增：验证码回调函数
) -> list[dict]:
    """
    抖音搜索整合流程（一步到位）：
    注意：Cookie应该在浏览器初始化时注入，这里不再重复注入

    1. （可选）注入本地保存的登录 Cookie
    2. 打开抖音首页
    3. 确认登录状态（仅打日志）
    4. 定位顶栏搜索框 [data-e2e='searchbar-input']，清空后输入 keyword
    5. 模拟点击搜索按钮 [data-e2e='searchbar-button']
    6. 等待结果页并解析视频列表返回
    7. 如果遇到验证码，等待用户完成

    :param page: Playwright Page（已创建好的浏览器页）
    :param keyword: 搜索关键词（用户指定）
    :param max_count: 最多返回视频条数
    :param inject_cookie: 是否在操作前注入本地抖音 Cookie，默认 False（避免重复注入）
    :param captcha_callback: 验证码提示回调函数（用于GUI显示）
    :return: 视频列表 [{"url","title","author","platform":"douyin"}, ...]
    """
    if inject_cookie:
        try:
            from douyin.auth import inject_douyin_cookies_to_page

            inject_douyin_cookies_to_page(page)
            logger.info("[抖音] 已重新注入Cookie（不推荐频繁操作）")
        except Exception as e:
            logger.warning(f"[抖音] 注入 Cookie 失败: {e}")

    from douyin.search import DouyinSearchManager

    mgr = DouyinSearchManager(page)
    return mgr.search_videos(
        keyword=keyword, max_count=max_count, captcha_callback=captcha_callback
    )
