# 抖音网页版页面选择器。
# 说明：抖音网页为 SPA，class 可能随版本变化，若自动化失败请按实际 DOM 调整。


class DouyinSelectors:
    """抖音网页版（douyin.com）常用元素选择器。"""

    # 登录 / 用户
    LOGIN = {
        "avatar": "[data-e2e='user-avatar'], .avatar-wrap, .header-avatar",
        "login_btn": "[data-e2e='login-button'], .login-entry, button:has-text('登录')",
    }

    # 搜索（首页顶栏）
    SEARCH = {
        # 搜索框：优先 data-e2e，与当前抖音 DOM 一致
        "search_input": "[data-e2e='searchbar-input']",
        "search_input_fallback": "input[placeholder*='搜索你感兴趣的内容'], input[placeholder*='搜索']",
        # 搜索按钮
        "search_btn": "[data-e2e='searchbar-button']",
        "search_btn_fallback": "button:has-text('搜索'), [data-e2e='search-button']",
        # 结果列表：抖音搜索结果为视频卡片，class 常为 hash 形式，用多种备选
        "video_card": (
            "[data-e2e='search-result-item'], "
            ".search-result-item, "
            ".video-card, "
            "li[class*='result'], "
            "a[href*='/video/']"
        ),
        "link": "a[href*='/video/']",
        "title": "[data-e2e='video-title'], .title, .video-title, h3",
        "author": "[data-e2e='video-author'], .author-name, .user-name",
        "stats": "[data-e2e='video-stats'], .stats, .play-count, .digg-count",
        "next_page": (
            "button:has-text('下一页'), "
            "[data-e2e='next-page'], "
            ".next-page, "
            ".pagination-next"
        ),
    }

    @staticmethod
    def get_search_video_cards() -> str:
        return DouyinSelectors.SEARCH["video_card"]

    @staticmethod
    def get_search_video_link() -> str:
        return DouyinSelectors.SEARCH["link"]

    @staticmethod
    def get_next_page() -> str:
        return DouyinSelectors.SEARCH["next_page"]
