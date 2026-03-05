# 抖音网页版搜索与列表自动化，与 core.search（B 站）无耦合。
# 流程：打开首页 → 确认登录态 → 定位搜索框输入 → 模拟点击搜索按钮。

from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from utils.logger import get_logger
from utils.retry import retry
from douyin.selectors import DouyinSelectors

if TYPE_CHECKING:
    from playwright.sync_api import Page

logger = get_logger()

DOUYIN_HOME = "https://www.douyin.com/"


def save_debug_snapshot(page: Page, prefix: str = "debug", reason: str = ""):
    """
    保存调试快照（截图 + HTML）

    :param page: Playwright Page 对象
    :param prefix: 文件名前缀
    :param reason: 保存原因
    """
    try:
        # 创建调试目录
        debug_dir = Path(__file__).parent.parent.parent / "debug_snapshots"
        debug_dir.mkdir(exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{prefix}_{timestamp}"

        # 保存截图
        screenshot_path = debug_dir / f"{base_name}.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"[调试] 截图已保存: {screenshot_path}")

        # 保存 HTML
        html_path = debug_dir / f"{base_name}.html"
        html_content = page.content()
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"[调试] HTML已保存: {html_path}")

        # 保存元数据
        meta_path = debug_dir / f"{base_name}_meta.txt"
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(f"时间: {datetime.now().isoformat()}\n")
            f.write(f"原因: {reason}\n")
            f.write(f"URL: {page.url}\n")
            f.write(f"标题: {page.title()}\n")
        logger.info(f"[调试] 元数据已保存: {meta_path}")

        return str(screenshot_path), str(html_path)

    except Exception as e:
        logger.error(f"[调试] 保存快照失败: {e}")
        return None, None


class DouyinSearchManager:
    """抖音网页版：首页、登录检查、搜索框输入+点击搜索、结果列表。"""

    def __init__(self, page: Page) -> None:
        self.page = page

    def open_homepage(self) -> bool:
        """打开抖音首页。"""
        try:
            # 抖音首页可能会自动跳转，使用 domcontentloaded 更快
            self.page.goto(DOUYIN_HOME, wait_until="domcontentloaded", timeout=15000)
            self.page.wait_for_timeout(2000)
            logger.info(f"[抖音] 已打开页面: {self.page.url}")
            return True
        except Exception as e:
            # 即使有跳转错误，只要页面加载了就继续
            logger.warning(f"[抖音] 打开首页时有跳转: {e}")
            try:
                # 检查页面是否已加载
                if "douyin.com" in self.page.url:
                    logger.info(f"[抖音] 页面已加载: {self.page.url}")
                    return True
            except:
                pass
            return False

    def check_captcha(self) -> bool:
        """
        检测是否出现验证码（包括滑块拼图验证码）

        :return: True表示有验证码，False表示没有
        """
        try:
            # 优先检查最明确的验证码标识
            high_priority_selectors = [
                # 验证码容器ID（最可靠）
                "#captcha_container",
                '[id*="captcha"]',
                # 验证码iframe
                'iframe[src*="captcha"]',
                'iframe[src*="verify"]',
                # 抖音特定验证码
                '[class*="secsdk-captcha"]',
                '[class*="captcha-verify"]',
            ]

            for selector in high_priority_selectors:
                try:
                    elem = self.page.locator(selector).first
                    if elem.count() > 0 and elem.is_visible():
                        logger.warning(f"[抖音] 检测到验证码元素: {selector}")
                        return True
                except:
                    continue

            # 检查验证码文字提示
            text_selectors = [
                "text=验证",
                "text=滑动验证",
                "text=点击验证",
                "text=拖动滑块",
                "text=安全验证",
                "text=请完成验证",
                "text=向右拖动滑块填充拼图",
                "text=拖动下方滑块完成拼图",
            ]

            for selector in text_selectors:
                try:
                    elem = self.page.locator(selector).first
                    if elem.count() > 0 and elem.is_visible():
                        logger.warning(f"[抖音] 检测到验证码文字: {selector}")
                        return True
                except:
                    continue

            # 检查页面URL是否包含验证码相关关键词
            current_url = self.page.url
            if any(
                keyword in current_url.lower()
                for keyword in ["captcha", "verify", "challenge"]
            ):
                logger.warning(f"[抖音] URL包含验证码关键词: {current_url}")
                return True

            # 注意：移除了canvas检测，因为视频播放器也使用canvas，容易误判
            # 只有在有明确验证码标识时才判断为验证码

            return False
        except Exception as e:
            logger.debug(f"[抖音] 验证码检测异常: {e}")
            return False

    def detect_captcha_type(self) -> str:
        """
        检测验证码类型

        :return: 验证码类型 - "slider"(滑块), "puzzle"(拼图), "click"(点击), "unknown"(未知)
        """
        try:
            # 检测滑块拼图
            slider_selectors = [
                '[class*="slider"]',
                '[class*="slide"]',
                "text=滑动",
                "text=拖动",
                "canvas[width]",
            ]

            for selector in slider_selectors:
                try:
                    elem = self.page.locator(selector).first
                    if elem.count() > 0 and elem.is_visible():
                        logger.info(f"[抖音] 检测到滑块/拼图验证码")
                        return "slider"
                except:
                    continue

            # 检测点击验证
            click_selectors = ["text=点击", "text=选择", '[class*="click"]']

            for selector in click_selectors:
                try:
                    elem = self.page.locator(selector).first
                    if elem.count() > 0 and elem.is_visible():
                        logger.info(f"[抖音] 检测到点击验证码")
                        return "click"
                except:
                    continue

            return "unknown"
        except Exception as e:
            logger.debug(f"[抖音] 验证码类型检测异常: {e}")
            return "unknown"

    def wait_for_captcha_completion(
        self, timeout: int = 60, callback=None, max_rounds: int = 3
    ):
        """
        等待用户完成验证码（支持多轮验证，包括滑块拼图）

        :param timeout: 每轮验证的超时时间（秒）
        :param callback: 回调函数，用于更新UI提示（可选）
        :param max_rounds: 最大验证轮数（默认3轮，应对多次验证）
        :return: True表示验证码已完成，False表示超时
        """
        import time

        logger.warning("[抖音] ⚠️ 检测到验证码，请在浏览器中完成验证")

        # 检测验证码类型
        captcha_type = self.detect_captcha_type()

        if captcha_type == "slider":
            logger.info("[抖音] 验证码类型: 滑块拼图验证")
            logger.info("[抖音] 提示: 请拖动滑块完成拼图验证")
            if callback:
                callback("[验证码] 检测到滑块拼图验证码")
                callback("[验证码] 请在浏览器中拖动滑块完成拼图")
        else:
            logger.info(f"[抖音] 验证码类型: {captcha_type}")
            if callback:
                callback("[验证码] 检测到验证码，请在浏览器窗口中完成验证")

        logger.info(
            f"[抖音] 等待验证码完成，超时时间: {timeout}秒/轮，最多 {max_rounds} 轮"
        )

        if callback:
            callback(f"[验证码] 等待时间: {timeout}秒/轮，最多 {max_rounds} 轮")

        for round_num in range(1, max_rounds + 1):
            if round_num > 1:
                logger.info(f"[抖音] 开始第 {round_num} 轮验证检测")
                if callback:
                    callback(f"[验证码] 第 {round_num} 轮验证检测...")

            start_time = time.time()
            check_interval = 1  # 每秒检查一次
            last_notify_time = 0
            notify_interval = 10  # 每10秒提示一次

            while time.time() - start_time < timeout:
                elapsed = int(time.time() - start_time)
                remaining = timeout - elapsed

                # 定期提示剩余时间
                if elapsed - last_notify_time >= notify_interval:
                    logger.info(f"[抖音] 验证码等待中... 剩余 {remaining} 秒")
                    if callback:
                        callback(f"[验证码] 等待中... 剩余 {remaining} 秒")
                    last_notify_time = elapsed

                # 检查验证码是否完成
                if not self.check_captcha():
                    logger.info(f"[抖音] ✓ 第 {round_num} 轮验证已完成")
                    if callback:
                        callback(f"[验证码] ✓ 第 {round_num} 轮验证已完成")

                    # 等待页面稳定
                    time.sleep(2)

                    # 再次检查是否有新的验证码（多轮验证）
                    time.sleep(1)
                    if self.check_captcha():
                        logger.warning(f"[抖音] ⚠️ 检测到第 {round_num + 1} 轮验证")
                        if callback:
                            callback(f"[验证码] ⚠️ 检测到额外验证，请继续完成")
                        break  # 跳出当前轮次，进入下一轮
                    else:
                        # 确实完成了，没有新的验证码
                        logger.info("[抖音] ✓ 所有验证已完成")
                        if callback:
                            callback("[验证码] ✓ 所有验证已完成，继续执行")
                        return True

                time.sleep(check_interval)

            # 当前轮次超时
            if self.check_captcha():
                logger.warning(f"[抖音] 第 {round_num} 轮验证等待超时")
                if callback:
                    callback(f"[验证码] 第 {round_num} 轮验证超时")

                # 如果还有剩余轮次，继续等待
                if round_num < max_rounds:
                    logger.info(f"[抖音] 继续等待下一轮验证...")
                    if callback:
                        callback(f"[验证码] 继续等待...")
                else:
                    logger.error("[抖音] 所有验证轮次均超时")
                    if callback:
                        callback("[验证码] ✗ 验证超时，请重试")
                    return False

        # 所有轮次都完成了
        logger.info("[抖音] 验证流程结束")
        return not self.check_captcha()

    def check_login_status(self) -> bool:
        """根据页面元素判断是否已登录：多重检测机制确保准确性。"""
        try:
            # 等待页面加载完成
            self.page.wait_for_timeout(2000)

            logger.info("[抖音] 开始多重登录状态检测")

            # 方法1: 检查 Cookie 中是否有关键登录信息（最可靠）
            try:
                cookies = self.page.context.cookies()
                login_cookies = ["sessionid", "sid_guard", "uid_tt"]

                # 检查是否有登录Cookie且有值
                found_cookies = []
                for c in cookies:
                    if c.get("name") in login_cookies and c.get("value"):
                        found_cookies.append(c.get("name"))

                if found_cookies:
                    logger.info(
                        f"[抖音] 检测到登录 Cookie: {', '.join(found_cookies)} - 已登录"
                    )
                    return True
                else:
                    logger.debug("[抖音] 未检测到关键登录Cookie")
            except Exception as e:
                logger.debug(f"[抖音] Cookie检测异常: {e}")

            # 方法2: 检查用户头像或用户信息（已登录的标志）
            avatar_selectors = [
                "[data-e2e='user-avatar']",
                "[class*='avatar']",
                "[class*='user-info']",
                "img[alt*='头像']",
            ]

            for selector in avatar_selectors:
                try:
                    avatar_elem = self.page.locator(selector).first
                    if avatar_elem.count() > 0 and avatar_elem.is_visible():
                        logger.info(f"[抖音] 检测到用户元素 ({selector}) - 已登录")
                        return True
                except:
                    continue

            logger.debug("[抖音] 未检测到用户头像元素")

            # 方法3: 检查是否有登录按钮（未登录的标志）
            login_selectors = [
                "button:has-text('登录')",
                "[class*='login']:has-text('登录')",
                "a:has-text('登录')",
            ]

            for selector in login_selectors:
                try:
                    login_elem = self.page.locator(selector).first
                    if login_elem.count() > 0 and login_elem.is_visible():
                        logger.info("[抖音] 检测到登录按钮 - 当前未登录")
                        return False
                except:
                    continue

            logger.debug("[抖音] 未检测到登录按钮")

            # 方法4: 检查页面内容
            try:
                page_content = self.page.content()
                # 已登录页面通常不会有"立即登录"等文字
                if "立即登录" in page_content or "扫码登录" in page_content:
                    logger.info("[抖音] 检测到登录提示文字 - 未登录")
                    return False
            except:
                pass

            # 如果有Cookie但没有明确的UI元素，倾向于判断为已登录
            # 因为Cookie是最可靠的登录凭证
            logger.warning("[抖音] 无法通过UI元素明确判断，但有Cookie，判断为已登录")
            return True  # 改为True，因为有Cookie就认为已登录

        except Exception as e:
            logger.error(f"[抖音] 检查登录态异常: {e}")
            # 异常情况下，检查是否有Cookie
            try:
                cookies = self.page.context.cookies()
                has_login_cookie = any(
                    c.get("name") in ["sessionid", "sid_guard", "uid_tt"]
                    and c.get("value")
                    for c in cookies
                )
                if has_login_cookie:
                    logger.info("[抖音] 异常情况下检测到Cookie - 判断为已登录")
                    return True
            except:
                pass
            return False

    def _get_search_input_locator(self):
        sel = DouyinSelectors.SEARCH["search_input"]
        loc = self.page.locator(sel)
        if loc.count() > 0:
            return loc.first
        return self.page.locator(DouyinSelectors.SEARCH["search_input_fallback"]).first

    def _get_search_btn_locator(self):
        sel = DouyinSelectors.SEARCH["search_btn"]
        loc = self.page.locator(sel)
        if loc.count() > 0:
            return loc.first
        return self.page.locator(DouyinSelectors.SEARCH["search_btn_fallback"]).first

    def _switch_to_video_tab(self) -> bool:
        """
        切换到视频标签页

        :return: 是否成功切换
        """
        try:
            import time
            import random

            logger.info("[抖音] 尝试切换到视频标签...")

            # 查找视频标签 (使用 data-key="video" 属性)
            video_tab_selector = 'span[data-key="video"]'
            video_tab = self.page.locator(video_tab_selector)

            # 等待标签出现
            try:
                video_tab.wait_for(state="visible", timeout=5000)
            except:
                logger.warning("[抖音] 未找到视频标签，可能已经在视频页面")
                # 检查 URL 是否已包含 type=video
                if "type=video" in self.page.url:
                    logger.info("[抖音] URL已包含 type=video，无需切换")
                    return True
                return False

            if video_tab.count() == 0:
                logger.warning("[抖音] 视频标签不存在")
                return False

            # 检查是否已经选中
            try:
                parent = video_tab.locator("..")
                parent_class = parent.get_attribute("class") or ""
                is_active = (
                    "active" in parent_class.lower()
                    or "selected" in parent_class.lower()
                )

                if is_active:
                    logger.info("[抖音] 视频标签已经是选中状态")
                    return True
            except:
                pass

            # 点击视频标签
            logger.info("[抖音] 点击视频标签...")
            video_tab.scroll_into_view_if_needed()
            time.sleep(random.uniform(0.3, 0.5))
            video_tab.click()

            # 等待页面更新
            time.sleep(random.uniform(1.5, 2.5))

            # 验证是否切换成功
            current_url = self.page.url
            if "type=video" in current_url:
                logger.info(f"[抖音] 成功切换到视频标签: {current_url}")
                return True
            else:
                logger.warning(f"[抖音] 切换后URL未包含type=video: {current_url}")
                return False

        except Exception as e:
            logger.error(f"[抖音] 切换视频标签失败: {e}")
            return False

    def _apply_filters(
        self, sort_by: str = "most_liked", time_range: str = "week"
    ) -> bool:
        """
        应用筛选条件（排序和时间范围）

        :param sort_by: 排序方式 - "comprehensive"(综合排序), "latest"(最新发布), "most_liked"(最多点赞)
        :param time_range: 时间范围 - "all"(不限), "day"(一天内), "week"(一周内), "half_year"(半年内)
        :return: 是否成功应用筛选
        """
        try:
            import time
            import random

            logger.info(f"[抖音] 应用筛选: 排序={sort_by}, 时间={time_range}")

            # 查找筛选按钮
            filter_button = self.page.locator('span:has-text("筛选")').first

            if filter_button.count() == 0:
                logger.warning("[抖音] 未找到筛选按钮")
                return False

            # 滚动到筛选按钮
            filter_button.scroll_into_view_if_needed()
            time.sleep(random.uniform(0.3, 0.5))

            # Hover 筛选按钮以显示下拉菜单
            logger.info("[抖音] Hover 筛选按钮...")
            filter_button.hover()
            time.sleep(random.uniform(1.0, 1.5))

            # 点击排序选项
            sort_text_map = {
                "comprehensive": "综合排序",
                "latest": "最新发布",
                "most_liked": "最多点赞",
            }

            sort_text = sort_text_map.get(sort_by, "最多点赞")
            logger.info(f"[抖音] 点击排序选项: {sort_text}")

            sort_option = self.page.locator(f'text="{sort_text}"').first
            if sort_option.count() > 0:
                try:
                    sort_option.wait_for(state="visible", timeout=3000)
                    sort_option.click()
                    logger.info(f"[抖音] 已点击排序: {sort_text}")
                    time.sleep(random.uniform(1.0, 1.5))
                except Exception as e:
                    logger.warning(f"[抖音] 点击排序失败: {e}")
            else:
                logger.warning(f"[抖音] 未找到排序选项: {sort_text}")

            # 再次 hover 筛选按钮以显示时间选项
            logger.info("[抖音] 再次 hover 筛选按钮...")
            filter_button.hover()
            time.sleep(random.uniform(1.0, 1.5))

            # 点击时间范围选项
            time_text_map = {
                "all": "不限",
                "day": "一天内",
                "week": "一周内",
                "half_year": "半年内",
            }

            time_text = time_text_map.get(time_range, "一周内")
            logger.info(f"[抖音] 点击时间范围: {time_text}")

            time_option = self.page.locator(f'text="{time_text}"').first
            if time_option.count() > 0:
                try:
                    time_option.wait_for(state="visible", timeout=3000)
                    time_option.click()
                    logger.info(f"[抖音] 已点击时间范围: {time_text}")
                    time.sleep(random.uniform(1.5, 2.0))
                except Exception as e:
                    logger.warning(f"[抖音] 点击时间范围失败: {e}")
            else:
                logger.warning(f"[抖音] 未找到时间范围选项: {time_text}")

            logger.info("[抖音] 筛选条件已应用")
            return True

        except Exception as e:
            logger.error(f"[抖音] 应用筛选失败: {e}")
            return False

            if video_tab.count() == 0:
                logger.warning("[抖音] 视频标签不存在")
                return False

            # 检查是否已经选中
            try:
                parent = video_tab.locator("..")
                parent_class = parent.get_attribute("class") or ""
                is_active = (
                    "active" in parent_class.lower()
                    or "selected" in parent_class.lower()
                )

                if is_active:
                    logger.info("[抖音] 视频标签已经是选中状态")
                    return True
            except:
                pass

            # 点击视频标签
            logger.info("[抖音] 点击视频标签...")
            video_tab.scroll_into_view_if_needed()
            time.sleep(random.uniform(0.3, 0.5))
            video_tab.click()

            # 等待页面更新
            time.sleep(random.uniform(1.5, 2.5))

            # 验证是否切换成功
            current_url = self.page.url
            if "type=video" in current_url:
                logger.info(f"[抖音] 成功切换到视频标签: {current_url}")
                return True
            else:
                logger.warning(f"[抖音] 切换后URL未包含type=video: {current_url}")
                return False

        except Exception as e:
            logger.error(f"[抖音] 切换视频标签失败: {e}")
            return False

    @retry(max_attempts=2, delay=2.0, exceptions=(PlaywrightTimeoutError, Exception))
    def search_videos(
        self,
        keyword: str,
        max_count: int = 20,
        reuse_page: bool = True,  # 新增参数：是否复用当前页面
        captcha_callback=None,  # 新增参数：验证码回调函数
    ) -> list[dict]:
        """
        搜索抖音视频（优化版 - 减少触发风控）

        优化点：
        1. 如果当前已在抖音页面，直接使用搜索框，不重新打开首页
        2. 添加随机延迟模拟真人操作
        3. 减少不必要的页面跳转
        4. 支持验证码检测和等待

        :param keyword: 搜索关键词
        :param max_count: 最多返回视频条数
        :param reuse_page: 是否复用当前页面（默认True，减少风控）
        :param captcha_callback: 验证码提示回调函数（用于GUI显示）
        :return: 视频列表
        """
        import random
        import time

        logger.info(
            f"[抖音] 搜索关键词: {keyword}, max_count={max_count}, reuse_page={reuse_page}"
        )
        try:
            # 检查当前是否已在抖音页面
            current_url = self.page.url
            is_on_douyin = "douyin.com" in current_url

            if not is_on_douyin or not reuse_page:
                # 只有不在抖音页面时才打开首页
                logger.info("[抖音] 当前不在抖音页面，打开首页")
                if not self.open_homepage():
                    return []

                # 检查打开首页后是否有验证码
                if self.check_captcha():
                    logger.warning("[抖音] 打开首页后检测到验证码")
                    if captcha_callback:
                        captcha_callback("[提示] 打开首页时触发验证码，请完成验证")
                    if not self.wait_for_captcha_completion(
                        timeout=60, callback=captcha_callback
                    ):
                        logger.error("[抖音] 首页验证码未完成")
                        return []

                self.check_login_status()
            else:
                logger.info(f"[抖音] 复用当前页面: {current_url}")
                # 添加随机延迟（1-2秒）
                delay = random.uniform(1.0, 2.0)
                logger.debug(f"[抖音] 随机延迟 {delay:.2f}秒")
                time.sleep(delay)

            # 定位搜索框并输入（模拟真实输入：先点击聚焦再逐字输入）
            logger.info("[抖音] 开始定位搜索框...")
            input_el = self._get_search_input_locator()
            input_el.wait_for(state="visible", timeout=10000)
            logger.info("[抖音] 搜索框已找到")

            # 模拟鼠标移动到搜索框
            input_el.scroll_into_view_if_needed()
            time.sleep(random.uniform(0.3, 0.6))

            logger.debug("[抖音] 点击搜索框")
            input_el.click()
            time.sleep(random.uniform(0.2, 0.4))

            logger.debug("[抖音] 清空搜索框")
            input_el.fill("")
            time.sleep(random.uniform(0.1, 0.3))

            # 逐字输入，模拟真人打字速度
            logger.info(f"[抖音] 输入关键词: {keyword}")
            input_el.type(keyword, delay=random.randint(80, 150))
            time.sleep(random.uniform(0.3, 0.6))

            # 模拟真实点击搜索按钮
            logger.info("[抖音] 查找搜索按钮...")
            btn = self._get_search_btn_locator()
            if btn.count() == 0 or not btn.is_visible():
                logger.warning("[抖音] 未找到搜索按钮")
                return []

            logger.info("[抖音] 点击搜索按钮")
            btn.scroll_into_view_if_needed()
            time.sleep(random.uniform(0.2, 0.4))
            btn.click()

            logger.info("[抖音] 搜索按钮已点击，等待页面跳转...")

            # 等待页面加载（随机延迟2-3秒）
            wait_time = random.uniform(2.0, 3.0)
            logger.debug(f"[抖音] 等待搜索结果加载 {wait_time:.2f}秒")
            self.page.wait_for_timeout(int(wait_time * 1000))

            logger.info(f"[抖音] 当前页面URL: {self.page.url}")

            # 检测是否出现验证码
            if self.check_captcha():
                logger.warning("[抖音] 搜索后检测到验证码，等待用户完成")
                if captcha_callback:
                    captcha_callback("[提示] 搜索触发验证码，请在浏览器中完成验证")

                if not self.wait_for_captcha_completion(
                    timeout=60, callback=captcha_callback
                ):
                    logger.error("[抖音] 验证码未完成，搜索失败")
                    if captcha_callback:
                        captcha_callback("[失败] 验证码未在规定时间内完成")
                    return []

                logger.info("[抖音] 验证码已完成，继续搜索")
                if captcha_callback:
                    captcha_callback("[成功] 验证码已完成，正在获取搜索结果...")
                # 验证码完成后再等待一下
                time.sleep(random.uniform(1.0, 2.0))

            # 获取搜索结果前再次检查验证码（防止额外验证）
            if self.check_captcha():
                logger.warning("[抖音] 获取结果前检测到额外验证")
                if captcha_callback:
                    captcha_callback("[提示] 检测到额外验证，请继续完成")

                if not self.wait_for_captcha_completion(
                    timeout=60, callback=captcha_callback, max_rounds=2
                ):
                    logger.error("[抖音] 额外验证未完成")
                    if captcha_callback:
                        captcha_callback("[失败] 额外验证未完成")
                    return []

                logger.info("[抖音] 额外验证已完成")
                if captcha_callback:
                    captcha_callback("[成功] 额外验证已完成")
                time.sleep(random.uniform(1.0, 2.0))

            # 切换到视频标签
            if not self._switch_to_video_tab():
                logger.warning("[抖音] 切换到视频标签失败，尝试继续获取结果")

            # 应用筛选条件（最多点赞 + 一周内）
            if not self._apply_filters(sort_by="most_liked", time_range="week"):
                logger.warning("[抖音] 应用筛选条件失败，使用默认排序")

            return self.get_current_page_videos(max_count)
        except Exception as e:
            logger.error(f"[抖音] 搜索流程出错: {e}")
            if captcha_callback:
                captcha_callback(f"[错误] 搜索出错: {str(e)}")
            return []

    def get_current_page_videos(self, max_count: int = 20) -> list[dict]:
        """从当前页面解析视频卡片，返回视频信息列表。"""
        try:
            # 先检查是否有验证码（可能在加载结果时出现）
            if self.check_captcha():
                logger.warning("[抖音] 解析结果时检测到验证码")
                # 保存验证码页面快照
                save_debug_snapshot(
                    self.page, "captcha_detected", "解析结果时检测到验证码"
                )
                return []

            logger.info(f"[抖音] 当前页面URL: {self.page.url}")

            # 等待页面内容加载
            import time

            time.sleep(2)

            # 使用 JavaScript 直接提取视频信息（更可靠）
            from douyin.extract_videos_js import EXTRACT_VIDEOS_JS

            extract_js = EXTRACT_VIDEOS_JS

            videos = self.page.evaluate(extract_js, max_count)
            logger.info(f"[抖音] JavaScript 提取到 {len(videos)} 个视频")

            if len(videos) > 0:
                # 转换为标准格式
                video_list = []
                for v in videos:
                    video_list.append(
                        {
                            "url": v["url"],
                            "title": v["title"],
                            "author": v.get("author", "Unknown"),
                            "platform": "douyin",
                        }
                    )
                    logger.debug(f"[抖音] 视频: {v['title'][:30]}... - {v['url']}")

                logger.info(f"[抖音] 成功提取 {len(video_list)} 个视频")
                # 保存成功提取的页面快照
                save_debug_snapshot(
                    self.page, "extract_success", f"成功提取 {len(video_list)} 个视频"
                )
                return video_list

            # 如果 JavaScript 方法也失败，保存快照并尝试传统方法
            logger.warning(
                "[抖音] JavaScript 方法未找到视频，保存快照并尝试传统选择器..."
            )
            save_debug_snapshot(
                self.page, "extract_failed_js", "JavaScript 方法未找到视频"
            )

            selectors = DouyinSelectors.SEARCH
            card_selector = selectors["video_card"]
            link_selector = selectors["link"]

            logger.debug(f"[抖音] 使用选择器: {link_selector}")

            try:
                logger.info("[抖音] 等待视频列表加载...")
                self.page.wait_for_selector(card_selector, timeout=10000)
                logger.info("[抖音] 视频列表已加载")
            except Exception as e:
                logger.warning(f"[抖音] 等待视频列表选择器超时: {e}")
                # 保存超时时的页面快照
                save_debug_snapshot(
                    self.page, "selector_timeout", f"等待选择器超时: {card_selector}"
                )

                # 再次检查是否是验证码导致的超时
                if self.check_captcha():
                    logger.warning("[抖音] 超时原因：出现验证码")
                    return []
                if self.page.locator("text=暂无结果").count() > 0:
                    logger.info("[抖音] 页面显示：暂无结果")
                    return []

                # 即使超时也尝试继续提取
                logger.info("[抖音] 选择器超时，但尝试继续提取...")

            # 获取所有视频链接
            links = self.page.locator(link_selector).all()
            logger.info(f"[抖音] 找到 {len(links)} 个链接元素")

            if len(links) == 0:
                # 尝试其他选择器
                logger.warning("[抖音] 未找到视频链接，尝试备用选择器...")

                # 尝试更通用的选择器
                alternative_selectors = [
                    "a[href*='/video/']",
                    "a[href*='douyin.com/video']",
                    "[data-e2e='search-result'] a",
                    ".search-result a[href*='/video/']",
                ]

                for alt_selector in alternative_selectors:
                    logger.debug(f"[抖音] 尝试选择器: {alt_selector}")
                    links = self.page.locator(alt_selector).all()
                    if len(links) > 0:
                        logger.info(f"[抖音] 使用备用选择器找到 {len(links)} 个链接")
                        break

                if len(links) == 0:
                    logger.error("[抖音] 所有选择器都未找到视频链接")
                    # 保存失败时的页面快照
                    save_debug_snapshot(
                        self.page, "no_links_found", "所有选择器都未找到视频链接"
                    )
                    # 输出页面内容用于调试
                    try:
                        page_text = self.page.content()[:500]
                        logger.debug(f"[抖音] 页面内容片段: {page_text}")
                    except:
                        pass
                    return []

            video_list: list[dict] = []
            seen_urls: set[str] = set()

            for idx, node in enumerate(links):
                if len(video_list) >= max_count:
                    break
                try:
                    url = node.get_attribute("href")
                    if not url:
                        logger.debug(f"[抖音] 链接 {idx} 没有 href 属性")
                        continue

                    # 过滤非视频链接
                    if "/video/" not in url:
                        logger.debug(f"[抖音] 跳过非视频链接: {url}")
                        continue

                    if not url.startswith("http"):
                        url = "https://www.douyin.com" + (
                            url if url.startswith("/") else "/" + url
                        )
                    url = url.split("?")[0]

                    if url in seen_urls:
                        logger.debug(f"[抖音] 跳过重复URL: {url}")
                        continue

                    seen_urls.add(url)

                    # 尝试获取标题
                    try:
                        title = (node.inner_text() or "").strip()
                        if not title or len(title) < 2:
                            # 尝试从父元素获取标题
                            parent = node.locator("xpath=..").first
                            title = (parent.inner_text() or "").strip()
                        if not title or len(title) < 2:
                            title = "Unknown"
                    except:
                        title = "Unknown"

                    author = "Unknown"

                    video_list.append(
                        {
                            "url": url,
                            "title": title,
                            "author": author,
                            "platform": "douyin",
                        }
                    )
                    logger.debug(
                        f"[抖音] 提取视频 {len(video_list)}: {title[:30]}... - {url}"
                    )

                except Exception as e:
                    logger.debug(f"[抖音] 提取链接 {idx} 失败: {e}")
                    continue

            logger.info(f"[抖音] 当前页提取 {len(video_list)} 个视频")

            if len(video_list) == 0:
                logger.warning("[抖音] 未提取到任何视频，可能需要更新选择器")
                # 保存最终失败的页面快照
                save_debug_snapshot(
                    self.page, "extract_failed_final", "未提取到任何视频"
                )
            else:
                # 保存成功提取的页面快照
                save_debug_snapshot(
                    self.page,
                    "extract_success_fallback",
                    f"使用备用方法提取 {len(video_list)} 个视频",
                )

            return video_list
        except Exception as e:
            logger.error(f"[抖音] 提取视频信息出错: {e}")
            import traceback

            logger.error(f"[抖音] 错误堆栈: {traceback.format_exc()}")
            # 保存异常时的页面快照
            try:
                save_debug_snapshot(
                    self.page, "extract_exception", f"提取视频异常: {str(e)}"
                )
            except:
                pass
            return []

            logger.info(f"[抖音] 当前页面URL: {self.page.url}")

            # 等待页面内容加载
            import time

            time.sleep(2)

            # 使用 JavaScript 直接提取视频信息（更可靠）
            logger.info("[抖音] 使用 JavaScript 提取视频信息...")

            extract_js = """
            (maxCount) => {
                const videos = [];
                const seenUrls = new Set();
                
                // 方法1: 查找所有可能的视频链接
                const linkSelectors = [
                    'a[href*="/video/"]',
                    'a[href*="douyin.com/video"]',
                    '[data-e2e*="search"] a',
                    '.search-result a',
                    'li a[href]'
                ];
                
                for (const selector of linkSelectors) {
                    const links = document.querySelectorAll(selector);
                    for (const link of links) {
                        if (videos.length >= maxCount) break;
                        
                        const href = link.href;
                        if (!href || !href.includes('/video/')) continue;
                        if (seenUrls.has(href)) continue;
                        
                        seenUrls.add(href);
                        
                        // 尝试获取标题
                        let title = link.innerText.trim();
                        if (!title || title.length < 2) {
                            // 尝试从父元素获取
                            const parent = link.closest('li, article, div[class*="item"]');
                            if (parent) {
                                title = parent.innerText.trim().split('\\n')[0];
                            }
                        }
                        
                        videos.push({
                            url: href.split('?')[0],
                            title: title || 'Unknown',
                            author: 'Unknown'
                        });
                    }
                    
                    if (videos.length >= maxCount) break;
                }
                
                // 方法2: 如果方法1没找到，尝试查找所有包含视频信息的元素
                if (videos.length === 0) {
                    const containers = document.querySelectorAll('li, article, [class*="item"]');
                    for (const container of containers) {
                        if (videos.length >= maxCount) break;
                        
                        const text = container.innerText;
                        if (!text || text.length < 10) continue;
                        
                        // 查找容器内的链接
                        const link = container.querySelector('a[href]');
                        if (!link) continue;
                        
                        const href = link.href;
                        if (!href.includes('douyin.com')) continue;
                        if (seenUrls.has(href)) continue;
                        
                        seenUrls.add(href);
                        
                        const title = text.split('\\n')[0].trim();
                        if (title.length > 2) {
                            videos.push({
                                url: href.split('?')[0],
                                title: title.substring(0, 100),
                                author: 'Unknown'
                            });
                        }
                    }
                }
                
                return videos;
            }
            """

            videos = self.page.evaluate(extract_js, max_count)
            logger.info(f"[抖音] JavaScript 提取到 {len(videos)} 个视频")

            if len(videos) > 0:
                # 转换为标准格式
                video_list = []
                for v in videos:
                    video_list.append(
                        {
                            "url": v["url"],
                            "title": v["title"],
                            "author": v.get("author", "Unknown"),
                            "platform": "douyin",
                        }
                    )
                    logger.debug(f"[抖音] 视频: {v['title'][:30]}... - {v['url']}")

                logger.info(f"[抖音] 成功提取 {len(video_list)} 个视频")
                return video_list

            # 如果 JavaScript 方法也失败，尝试传统方法
            logger.warning("[抖音] JavaScript 方法未找到视频，尝试传统选择器...")

            selectors = DouyinSelectors.SEARCH
            card_selector = selectors["video_card"]
            link_selector = selectors["link"]

            logger.debug(f"[抖音] 使用选择器: {link_selector}")

            try:
                logger.info("[抖音] 等待视频列表加载...")
                self.page.wait_for_selector(card_selector, timeout=10000)
                logger.info("[抖音] 视频列表已加载")
            except Exception as e:
                logger.warning(f"[抖音] 等待视频列表选择器超时: {e}")
                # 再次检查是否是验证码导致的超时
                if self.check_captcha():
                    logger.warning("[抖音] 超时原因：出现验证码")
                    return []
                if self.page.locator("text=暂无结果").count() > 0:
                    logger.info("[抖音] 页面显示：暂无结果")
                    return []

                # 即使超时也尝试继续提取
                logger.info("[抖音] 选择器超时，但尝试继续提取...")

            # 获取所有视频链接
            links = self.page.locator(link_selector).all()
            logger.info(f"[抖音] 找到 {len(links)} 个链接元素")

            if len(links) == 0:
                # 尝试其他选择器
                logger.warning("[抖音] 未找到视频链接，尝试备用选择器...")

                # 尝试更通用的选择器
                alternative_selectors = [
                    "a[href*='/video/']",
                    "a[href*='douyin.com/video']",
                    "[data-e2e='search-result'] a",
                    ".search-result a[href*='/video/']",
                ]

                for alt_selector in alternative_selectors:
                    logger.debug(f"[抖音] 尝试选择器: {alt_selector}")
                    links = self.page.locator(alt_selector).all()
                    if len(links) > 0:
                        logger.info(f"[抖音] 使用备用选择器找到 {len(links)} 个链接")
                        break

                if len(links) == 0:
                    logger.error("[抖音] 所有选择器都未找到视频链接")
                    # 输出页面内容用于调试
                    try:
                        page_text = self.page.content()[:500]
                        logger.debug(f"[抖音] 页面内容片段: {page_text}")
                    except:
                        pass
                    return []

            video_list: list[dict] = []
            seen_urls: set[str] = set()

            for idx, node in enumerate(links):
                if len(video_list) >= max_count:
                    break
                try:
                    url = node.get_attribute("href")
                    if not url:
                        logger.debug(f"[抖音] 链接 {idx} 没有 href 属性")
                        continue

                    # 过滤非视频链接
                    if "/video/" not in url:
                        logger.debug(f"[抖音] 跳过非视频链接: {url}")
                        continue

                    if not url.startswith("http"):
                        url = "https://www.douyin.com" + (
                            url if url.startswith("/") else "/" + url
                        )
                    url = url.split("?")[0]

                    if url in seen_urls:
                        logger.debug(f"[抖音] 跳过重复URL: {url}")
                        continue

                    seen_urls.add(url)

                    # 尝试获取标题
                    try:
                        title = (node.inner_text() or "").strip()
                        if not title or len(title) < 2:
                            # 尝试从父元素获取标题
                            parent = node.locator("xpath=..").first
                            title = (parent.inner_text() or "").strip()
                        if not title or len(title) < 2:
                            title = "Unknown"
                    except:
                        title = "Unknown"

                    author = "Unknown"

                    video_list.append(
                        {
                            "url": url,
                            "title": title,
                            "author": author,
                            "platform": "douyin",
                        }
                    )
                    logger.debug(
                        f"[抖音] 提取视频 {len(video_list)}: {title[:30]}... - {url}"
                    )

                except Exception as e:
                    logger.debug(f"[抖音] 提取链接 {idx} 失败: {e}")
                    continue

            logger.info(f"[抖音] 当前页提取 {len(video_list)} 个视频")

            if len(video_list) == 0:
                logger.warning("[抖音] 未提取到任何视频，可能需要更新选择器")

            return video_list
        except Exception as e:
            logger.error(f"[抖音] 提取视频信息出错: {e}")
            import traceback

            logger.error(f"[抖音] 错误堆栈: {traceback.format_exc()}")
            return []

            logger.info(f"[抖音] 当前页面URL: {self.page.url}")

            selectors = DouyinSelectors.SEARCH
            card_selector = selectors["video_card"]
            link_selector = selectors["link"]

            logger.debug(f"[抖音] 使用选择器: {link_selector}")

            try:
                logger.info("[抖音] 等待视频列表加载...")
                self.page.wait_for_selector(card_selector, timeout=10000)
                logger.info("[抖音] 视频列表已加载")
            except Exception as e:
                logger.warning(f"[抖音] 等待视频列表选择器超时: {e}")
                # 再次检查是否是验证码导致的超时
                if self.check_captcha():
                    logger.warning("[抖音] 超时原因：出现验证码")
                    return []
                if self.page.locator("text=暂无结果").count() > 0:
                    logger.info("[抖音] 页面显示：暂无结果")
                    return []

                # 即使超时也尝试继续提取
                logger.info("[抖音] 选择器超时，但尝试继续提取...")

            # 获取所有视频链接
            links = self.page.locator(link_selector).all()
            logger.info(f"[抖音] 找到 {len(links)} 个链接元素")

            if len(links) == 0:
                # 尝试其他选择器
                logger.warning("[抖音] 未找到视频链接，尝试备用选择器...")

                # 尝试更通用的选择器
                alternative_selectors = [
                    "a[href*='/video/']",
                    "a[href*='douyin.com/video']",
                    "[data-e2e='search-result'] a",
                    ".search-result a[href*='/video/']",
                ]

                for alt_selector in alternative_selectors:
                    logger.debug(f"[抖音] 尝试选择器: {alt_selector}")
                    links = self.page.locator(alt_selector).all()
                    if len(links) > 0:
                        logger.info(f"[抖音] 使用备用选择器找到 {len(links)} 个链接")
                        break

                if len(links) == 0:
                    logger.error("[抖音] 所有选择器都未找到视频链接")
                    # 输出页面内容用于调试
                    try:
                        page_text = self.page.content()[:500]
                        logger.debug(f"[抖音] 页面内容片段: {page_text}")
                    except:
                        pass
                    return []

            video_list: list[dict] = []
            seen_urls: set[str] = set()

            for idx, node in enumerate(links):
                if len(video_list) >= max_count:
                    break
                try:
                    url = node.get_attribute("href")
                    if not url:
                        logger.debug(f"[抖音] 链接 {idx} 没有 href 属性")
                        continue

                    # 过滤非视频链接
                    if "/video/" not in url:
                        logger.debug(f"[抖音] 跳过非视频链接: {url}")
                        continue

                    if not url.startswith("http"):
                        url = "https://www.douyin.com" + (
                            url if url.startswith("/") else "/" + url
                        )
                    url = url.split("?")[0]

                    if url in seen_urls:
                        logger.debug(f"[抖音] 跳过重复URL: {url}")
                        continue

                    seen_urls.add(url)

                    # 尝试获取标题
                    try:
                        title = (node.inner_text() or "").strip()
                        if not title or len(title) < 2:
                            # 尝试从父元素获取标题
                            parent = node.locator("xpath=..").first
                            title = (parent.inner_text() or "").strip()
                        if not title or len(title) < 2:
                            title = "Unknown"
                    except:
                        title = "Unknown"

                    author = "Unknown"

                    video_list.append(
                        {
                            "url": url,
                            "title": title,
                            "author": author,
                            "platform": "douyin",
                        }
                    )
                    logger.debug(
                        f"[抖音] 提取视频 {len(video_list)}: {title[:30]}... - {url}"
                    )

                except Exception as e:
                    logger.debug(f"[抖音] 提取链接 {idx} 失败: {e}")
                    continue

            logger.info(f"[抖音] 当前页提取 {len(video_list)} 个视频")

            if len(video_list) == 0:
                logger.warning("[抖音] 未提取到任何视频，可能需要更新选择器")

            return video_list
        except Exception as e:
            logger.error(f"[抖音] 提取视频信息出错: {e}")
            import traceback

            logger.error(f"[抖音] 错误堆栈: {traceback.format_exc()}")
            return []

    def go_to_next_page(self) -> bool:
        """点击下一页（若存在）。"""
        try:
            next_sel = DouyinSelectors.get_next_page()
            next_btn = self.page.locator(next_sel).first
            if next_btn.count() > 0 and next_btn.is_visible():
                next_btn.click()
                self.page.wait_for_timeout(2000)
                return True
            return False
        except Exception as e:
            logger.error(f"[抖音] 翻页失败: {e}")
            return False

    def click_video_card(
        self,
        video_id: str,
        wait_for_load: bool = True,
        use_direct_navigation: bool = True,
        captcha_callback=None,
    ) -> bool:
        """
        点击视频卡片进入详情页（支持验证码检测）

        :param video_id: 视频ID
        :param wait_for_load: 是否等待页面加载
        :param use_direct_navigation: 是否使用直接导航（更可靠）
        :param captcha_callback: 验证码提示回调函数
        :return: 是否成功
        """
        try:
            logger.info(f"[抖音] 进入视频详情页: {video_id}")

            if use_direct_navigation:
                # 方法1: 直接导航到视频URL（最可靠）
                video_url = f"https://www.douyin.com/video/{video_id}"
                logger.info(f"[抖音] 直接导航到: {video_url}")

                self.page.goto(video_url, wait_until="domcontentloaded", timeout=30000)

                if wait_for_load:
                    import time

                    time.sleep(2)

                    # 检测是否触发验证码
                    if self.check_captcha():
                        logger.warning(f"[抖音] 点击视频 {video_id} 触发验证码")
                        if captcha_callback:
                            captcha_callback(f"[验证码] 点击视频触发验证码，请完成验证")

                        # 保存验证码快照
                        save_debug_snapshot(
                            self.page,
                            "captcha_on_video_click",
                            f"点击视频 {video_id} 触发验证码",
                        )

                        # 等待用户完成验证码
                        if not self.wait_for_captcha_completion(
                            timeout=60, callback=captcha_callback
                        ):
                            logger.error(f"[抖音] 视频 {video_id} 验证码未完成")
                            if captcha_callback:
                                captcha_callback("[验证码] 验证超时，跳过此视频")
                            return False

                        logger.info(f"[抖音] 验证码已完成，继续处理视频 {video_id}")
                        if captcha_callback:
                            captcha_callback("[验证码] 验证完成，继续处理")

                        # 验证码完成后再等待一下
                        time.sleep(2)

                    # 验证是否成功加载
                    current_url = self.page.url
                    if f"/video/{video_id}" in current_url:
                        logger.info(f"[抖音] 成功进入视频详情页: {current_url}")
                        return True
                    else:
                        logger.warning(f"[抖音] 导航失败，当前URL: {current_url}")
                        return False

                return True
            else:
                # 方法2: 使用 Playwright 点击（可能不稳定）
                from douyin.click_video_js import CLICK_VIDEO_CARD_JS

                logger.info(f"[抖音] 使用点击方式")

                # 先滚动到元素
                container_id = f"waterfall_item_{video_id}"
                container = self.page.locator(f"#{container_id}")

                if container.count() == 0:
                    logger.error(f"[抖音] 未找到容器: {container_id}")
                    return False

                card = container.locator(".search-result-card").first
                if card.count() == 0:
                    logger.error(f"[抖音] 未找到卡片")
                    return False

                # 滚动到视图
                card.scroll_into_view_if_needed()
                import time

                time.sleep(0.5)

                # 点击
                card.click()
                logger.info(f"[抖音] 已点击卡片")

                if wait_for_load:
                    time.sleep(2)

                    # 验证是否跳转
                    current_url = self.page.url
                    if f"/video/{video_id}" in current_url or "modal_id" in current_url:
                        logger.info(f"[抖音] 成功打开视频: {current_url}")
                        return True
                    else:
                        logger.warning(f"[抖音] URL未变化: {current_url}")
                        return False

                return True

        except Exception as e:
            logger.error(f"[抖音] 进入视频详情页失败: {e}")
            import traceback

            logger.error(f"[抖音] 错误堆栈: {traceback.format_exc()}")
            return False

    def get_video_detail_info(self, wait_for_content: bool = True) -> dict:
        """
        获取视频详情页信息

        :param wait_for_content: 是否等待内容加载
        :return: 视频详情信息
        """
        try:
            from douyin.click_video_js import GET_VIDEO_DETAIL_INFO_JS

            logger.info("[抖音] 提取视频详情信息...")

            if wait_for_content:
                # 等待页面内容加载
                try:
                    # 等待 h1 标签出现（视频标题）
                    self.page.wait_for_selector("h1", timeout=10000)
                    logger.info("[抖音] 页面内容已加载")
                except Exception as e:
                    logger.warning(f"[抖音] 等待内容加载超时: {e}")

            info = self.page.evaluate(GET_VIDEO_DETAIL_INFO_JS)

            logger.info(f"[抖音] 视频标题: {info.get('title', 'Unknown')}")
            logger.info(f"[抖音] 作者: {info.get('author', 'Unknown')}")
            logger.info(f"[抖音] 点赞数: {info.get('likes', 'Unknown')}")

            return info

        except Exception as e:
            logger.error(f"[抖音] 提取视频详情失败: {e}")
            return {}

    def click_comment_button(self) -> bool:
        """
        点击评论按钮打开评论区（支持响应式布局）

        在窄屏幕下，评论区可能不是通过按钮打开，而是需要滚动到页面下方

        :return: 是否成功打开评论区
        """
        try:
            import time
            import random

            logger.info("[抖音] 尝试打开评论区...")

            # 先检查页面宽度，判断是否是响应式布局
            viewport_width = self.page.evaluate("() => window.innerWidth")
            logger.info(f"[抖音] 当前页面宽度: {viewport_width}px")

            # 如果宽度较小（小于1200px），评论区可能在下方，需要滚动
            if viewport_width < 1200:
                logger.info("[抖音] 检测到窄屏幕布局，尝试滚动到评论区...")
                return self._scroll_to_comments()

            # 宽屏幕下，尝试点击评论按钮
            logger.info("[抖音] 宽屏幕布局，查找评论按钮...")

            # 使用 data-e2e 属性查找评论按钮
            comment_button_selector = '[data-e2e="feed-comment-icon"]'
            comment_button = self.page.locator(comment_button_selector).first

            if comment_button.count() == 0:
                logger.warning("[抖音] 未找到评论按钮，尝试滚动到评论区...")
                return self._scroll_to_comments()

            logger.info("[抖音] 找到评论按钮")

            # 获取评论数
            try:
                comment_count_elem = comment_button.locator(".X_wB9MpJ, .RfKJW3Qx")
                if comment_count_elem.count() > 0:
                    comment_count = comment_count_elem.first.inner_text()
                    logger.info(f"[抖音] 评论数: {comment_count}")
            except:
                pass

            # 滚动到评论按钮
            comment_button.scroll_into_view_if_needed()
            time.sleep(random.uniform(0.3, 0.5))

            # 点击评论按钮
            logger.info("[抖音] 点击评论按钮...")
            comment_button.click()

            # 等待评论区加载
            time.sleep(random.uniform(2.0, 3.0))

            # 验证评论区是否出现
            if self._check_comment_area_visible():
                logger.info("[抖音] 评论区已打开")
                return True
            else:
                logger.warning("[抖音] 点击后评论区未出现，尝试滚动...")
                return self._scroll_to_comments()

        except Exception as e:
            logger.error(f"[抖音] 打开评论区失败: {e}")
            # 最后尝试滚动
            try:
                return self._scroll_to_comments()
            except:
                return False

    def _scroll_to_comments(self) -> bool:
        """
        滚动到评论区（用于响应式布局或窄屏幕）

        :return: 是否成功找到评论区
        """
        try:
            import time

            logger.info("[抖音] 开始滚动页面查找评论区...")

            # 先滚动到页面底部
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

            # 检查评论区是否可见
            if self._check_comment_area_visible():
                logger.info("[抖音] 滚动后找到评论区")
                return True

            # 尝试多次滚动加载
            for i in range(3):
                logger.info(f"[抖音] 第 {i + 1} 次滚动加载...")

                # 滚动到页面中部
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                time.sleep(0.5)

                # 再滚动到底部
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1.5)

                # 检查评论区
                if self._check_comment_area_visible():
                    logger.info("[抖音] 滚动后找到评论区")
                    return True

            logger.warning("[抖音] 滚动后仍未找到评论区")
            return False

        except Exception as e:
            logger.error(f"[抖音] 滚动到评论区失败: {e}")
            return False

    def _check_comment_area_visible(self) -> bool:
        """
        检查评论区是否可见

        :return: 评论区是否可见
        """
        try:
            # 检查多个可能的评论区选择器
            comment_selectors = [
                "#merge-all-comment-container",
                '[data-e2e="comment-list"]',
                '[data-e2e="comment-item"]',
                '[class*="comment"]',
            ]

            for selector in comment_selectors:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    # 检查是否可见
                    first_elem = elements.first
                    if first_elem.is_visible():
                        logger.debug(f"[抖音] 找到可见的评论区元素: {selector}")
                        return True

            return False

        except Exception as e:
            logger.debug(f"[抖音] 检查评论区可见性失败: {e}")
            return False

    def _scroll_load_comments(self, target_count: int = 20):
        """
        滚动加载更多评论

        :param target_count: 目标评论数量
        """
        try:
            import time

            logger.info(f"[抖音] 开始滚动加载评论，目标 {target_count} 条...")

            # 最多滚动5次
            for i in range(5):
                # 获取当前评论数
                current_count = self.page.locator('[data-e2e="comment-item"]').count()

                if current_count >= target_count:
                    logger.info(f"[抖音] 已加载足够评论: {current_count} 条")
                    break

                logger.info(f"[抖音] 第 {i + 1} 次滚动，当前评论数: {current_count}")

                # 滚动到评论区底部
                self.page.evaluate("""
                    () => {
                        // 查找评论区容器
                        const commentContainer = document.querySelector('#merge-all-comment-container') 
                            || document.querySelector('[data-e2e="comment-list"]')
                            || document.querySelector('[class*="comment"]');
                        
                        if (commentContainer) {
                            // 滚动到容器底部
                            commentContainer.scrollTop = commentContainer.scrollHeight;
                        } else {
                            // 如果没找到容器，滚动整个页面
                            window.scrollTo(0, document.body.scrollHeight);
                        }
                    }
                """)

                # 等待加载
                time.sleep(1.5)

                # 检查是否有新评论加载
                new_count = self.page.locator('[data-e2e="comment-item"]').count()
                if new_count == current_count:
                    logger.info(f"[抖音] 没有更多评论了，停止滚动")
                    break

            final_count = self.page.locator('[data-e2e="comment-item"]').count()
            logger.info(f"[抖音] 滚动完成，共加载 {final_count} 条评论")

        except Exception as e:
            logger.warning(f"[抖音] 滚动加载评论失败: {e}")

    def get_comments(self, max_count: int = 20) -> list[dict]:
        """
        获取评论区的评论信息（支持滚动加载）

        :param max_count: 最多获取评论数
        :return: 评论列表
        """
        try:
            import time

            logger.info(f"[抖音] 开始获取评论，最多 {max_count} 条...")

            # 等待评论区加载
            time.sleep(2)

            # 检查评论区是否存在
            if not self._check_comment_area_visible():
                logger.warning("[抖音] 评论区不可见")
                return []

            # 滚动加载更多评论
            self._scroll_load_comments(max_count)

            # 查找所有评论项
            comment_items = self.page.locator('[data-e2e="comment-item"]')
            comment_count = comment_items.count()

            logger.info(f"[抖音] 找到 {comment_count} 条评论")

            if comment_count == 0:
                logger.warning("[抖音] 未找到评论项，尝试其他选择器...")
                # 尝试其他选择器
                alternative_selectors = [
                    '[class*="comment-item"]',
                    '[class*="CommentItem"]',
                    'li[class*="comment"]',
                ]

                for selector in alternative_selectors:
                    comment_items = self.page.locator(selector)
                    comment_count = comment_items.count()
                    if comment_count > 0:
                        logger.info(
                            f"[抖音] 使用备用选择器找到 {comment_count} 条评论: {selector}"
                        )
                        break

                if comment_count == 0:
                    return []

            comments = []

            # 提取评论信息的 JavaScript
            extract_comment_js = """
            (element) => {
                const info = {
                    username: '',
                    user_id: '',
                    avatar: '',
                    content: '',
                    likes: '',
                    time: '',
                    reply_count: ''
                };
                
                try {
                    // 提取用户名 - 查找用户链接
                    const userLink = element.querySelector('a[href*="/user/"]');
                    if (userLink) {
                        info.username = userLink.innerText.trim();
                        // 提取用户ID
                        const href = userLink.getAttribute('href');
                        if (href) {
                            const match = href.match(/\\/user\\/([^?]+)/);
                            if (match) {
                                info.user_id = match[1];
                            }
                        }
                    }
                    
                    // 提取头像
                    const avatar = element.querySelector('img[alt*="头像"], img[class*="avatar"], img[class*="Avatar"]');
                    if (avatar) {
                        info.avatar = avatar.src;
                    }
                    
                    // 提取评论内容 - 查找评论文本区域
                    const contentSelectors = [
                        '[class*="comment-text"]',
                        '[class*="CommentText"]',
                        '[data-e2e="comment-content"]',
                        'p[class*="text"]',
                        'span[class*="text"]'
                    ];
                    
                    for (const selector of contentSelectors) {
                        const contentElem = element.querySelector(selector);
                        if (contentElem) {
                            const text = contentElem.innerText.trim();
                            if (text && text.length > 5) {
                                info.content = text;
                                break;
                            }
                        }
                    }
                    
                    // 如果还没找到内容，尝试获取所有文本
                    if (!info.content) {
                        const allText = element.innerText;
                        // 移除用户名后的文本作为评论内容
                        if (info.username && allText.includes(info.username)) {
                            const contentAfterUsername = allText.split(info.username)[1];
                            if (contentAfterUsername) {
                                info.content = contentAfterUsername.trim().split('\\n')[0];
                            }
                        }
                    }
                    
                    // 提取点赞数
                    const likeSelectors = [
                        '[class*="like-count"]',
                        '[class*="LikeCount"]',
                        '[data-e2e="comment-like-count"]'
                    ];
                    
                    for (const selector of likeSelectors) {
                        const likeElem = element.querySelector(selector);
                        if (likeElem) {
                            const text = likeElem.innerText.trim();
                            if (text && /\\d/.test(text)) {
                                info.likes = text;
                                break;
                            }
                        }
                    }
                    
                    // 提取时间
                    const timeSelectors = [
                        '[class*="time"]',
                        '[class*="Time"]',
                        '[class*="date"]',
                        '[class*="Date"]'
                    ];
                    
                    for (const selector of timeSelectors) {
                        const timeElem = element.querySelector(selector);
                        if (timeElem) {
                            const text = timeElem.innerText.trim();
                            if (text && (text.includes('前') || text.includes('天') || text.includes('小时') || text.includes('分钟'))) {
                                info.time = text;
                                break;
                            }
                        }
                    }
                    
                    // 提取回复数
                    const replySelectors = [
                        '[class*="reply-count"]',
                        '[class*="ReplyCount"]',
                        '[data-e2e="comment-reply-count"]'
                    ];
                    
                    for (const selector of replySelectors) {
                        const replyElem = element.querySelector(selector);
                        if (replyElem) {
                            const text = replyElem.innerText.trim();
                            if (text && /\\d/.test(text)) {
                                info.reply_count = text;
                                break;
                            }
                        }
                    }
                    
                } catch (e) {
                    console.error('[抖音评论] 提取失败:', e);
                }
                
                return info;
            }
            """

            # 提取评论
            for i in range(min(max_count, comment_count)):
                try:
                    comment_item = comment_items.nth(i)
                    comment_info = self.page.evaluate(
                        extract_comment_js, comment_item.element_handle()
                    )

                    # 只添加有内容的评论
                    if comment_info.get("content"):
                        comments.append(comment_info)
                        logger.debug(
                            f"[抖音] 评论 {i + 1}: {comment_info.get('username')} - {comment_info.get('content')[:30]}..."
                        )

                except Exception as e:
                    logger.warning(f"[抖音] 提取第 {i + 1} 条评论失败: {e}")
                    continue

            logger.info(f"[抖音] 成功提取 {len(comments)} 条评论")
            return comments

        except Exception as e:
            logger.error(f"[抖音] 获取评论失败: {e}")
            import traceback

            logger.error(f"[抖音] 错误堆栈: {traceback.format_exc()}")
            return []
