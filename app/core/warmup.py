import time
import random
import threading
from typing import Optional
from loguru import logger
from playwright.sync_api import Page, BrowserContext
from core.context import context as global_context
from core.captcha_check import check_captcha_on_page

class WarmupManager:
    def __init__(self, context: BrowserContext, config: dict, captcha_notifier: Optional[object] = None, reuse_page: Optional[Page] = None):
        self.context = context
        self.config = config
        self.warmup_config = config.get('warmup', {})
        self.captcha_notifier = captcha_notifier
        self.reuse_page = reuse_page  # 可选：复用现有页面，避免弹出新窗口
        self.running = True
        self._stop_event = threading.Event()

        # Stats
        self.watched_count = 0
        self.total_time_seconds = 0
        self.like_count = 0
        self.comment_count = 0

    def stop(self):
        self.running = False
        self._stop_event.set()

    def _interruptible_sleep(self, seconds: float) -> bool:
        """Sleep that can be interrupted by stop signal.
        Returns True if interrupted (should stop), False if completed normally."""
        return self._stop_event.wait(seconds)

    def _wait_captcha_resolved(self, page: Page, detail_url: str = "") -> bool:
        """检测到验证码时：停止操作，原地轮询等待用户解决；解决后返回 True，若收到停止信号返回 False。"""
        notified = False
        while self.running and check_captcha_on_page(page):
            if not notified:
                logger.warning("[养号] 检测到验证码，已停止操作，请在弹出的页面中完成验证...")
                if self.captcha_notifier:
                    self.captcha_notifier.notify_captcha_alert("warmup", detail_url or page.url or "")
                notified = True
            if self._interruptible_sleep(5):
                return False
        return True

    def run(self, status_callback=None, duration_override: int = None):
        """Main loop for warmup task

        Args:
            status_callback: 状态回调函数
            duration_override: 覆盖配置中的养号时长（分钟），用于验证码冷却流程
        """
        duration_minutes = duration_override if duration_override is not None else self.warmup_config.get('basic', {}).get('duration_minutes', 30)
        max_videos = self.warmup_config.get('basic', {}).get('max_videos', 20)
        end_time = time.time() + (duration_minutes * 60)

        logger.info(f"开始养号任务，预计时长: {duration_minutes} 分钟，目标视频数: {max_videos}")

        # 优先复用现有页面，避免弹出新窗口打扰用户
        if self.reuse_page:
            page = self.reuse_page
            should_close_page = False
            logger.debug("[养号] 复用现有浏览器页面，不弹出新窗口")
        else:
            page = self.context.new_page()
            should_close_page = True
            logger.debug("[养号] 创建新浏览器页面")

        global_context.page = page

        try:
            is_first_visit = True
            
            while self.running and time.time() < end_time and self.watched_count < max_videos:
                if is_first_visit:
                    logger.info("正在前往 B 站首页...")
                    page.goto("https://www.bilibili.com", wait_until="domcontentloaded", timeout=60000)
                    is_first_visit = False
                else:
                    logger.info("返回 B 站首页...")
                    page.goto("https://www.bilibili.com", wait_until="domcontentloaded", timeout=60000)
                
                if check_captcha_on_page(page):
                    if not self._wait_captcha_resolved(page, page.url):
                        break
                    logger.info("验证码已解决，继续养号...")
                
                video_cards = self._wait_for_video_cards(page)
                
                if not video_cards:
                    logger.warning("未能在首页找到推荐视频，尝试滚动页面...")
                    page.evaluate("window.scrollBy(0, 600)")
                    if self._interruptible_sleep(3): break
                    video_cards = self._wait_for_video_cards(page)
                
                if not video_cards:
                    logger.warning("仍未找到视频，尝试点击换一换...")
                    self._click_refresh_button(page)
                    if self._interruptible_sleep(3): break
                    video_cards = self._wait_for_video_cards(page)
                
                if not video_cards:
                    logger.error("多次尝试后仍未找到推荐视频，等待后重试...")
                    if self._interruptible_sleep(10): break
                    continue

                # 检查列表非空后再使用 random.choice
                if len(video_cards) == 0:
                    logger.warning("视频卡片列表为空，跳过...")
                    continue

                target_card = random.choice(video_cards)
                video_title, video_url = self._extract_video_info(target_card)
                
                if not video_url:
                    logger.warning("无法获取视频链接，跳过...")
                    continue
                
                logger.info(f"选中视频: {video_title}")
                
                self._watch_video(page, video_url, video_title, status_callback)
                
                self.watched_count += 1
                if status_callback:
                    status_callback(
                        video_title, 
                        self.watched_count, 
                        round(self.total_time_seconds / 60, 1), 
                        self.like_count,
                        self.comment_count
                    )
                
                delay = random.uniform(3, 10)
                logger.info(f"视频观看结束，随机等待 {delay:.1f} 秒...")
                if self._interruptible_sleep(delay):
                    logger.info("等待期间收到停止信号。")
                    break
                
        except Exception as e:
            logger.error(f"养号过程中发生错误: {e}")
        finally:
            # 只关闭自己创建的页面，复用的页面由调用方管理
            if should_close_page:
                page.close()
                logger.debug("[养号] 关闭养号页面")
            else:
                logger.debug("[养号] 保留复用的页面，由调用方管理")
            logger.info(f"养号任务结束。共观看 {self.watched_count} 个视频，累计时长 {self.total_time_seconds / 60:.1f} 分钟。")

    def _wait_for_video_cards(self, page: Page, timeout=15000):
        selectors = [
            ".bili-video-card",
            ".feed-card",
            ".recommended-container_det498 .video-card",
        ]
        for selector in selectors:
            try:
                # 检查停止信号
                if self._stop_event.is_set():
                    logger.debug("[养号] 等待视频卡片前检测到停止信号")
                    return []

                page.wait_for_selector(selector, timeout=timeout)

                # 检查停止信号
                if self._stop_event.is_set():
                    logger.debug("[养号] 等待视频卡片后检测到停止信号")
                    return []

                cards = page.query_selector_all(selector)
                if cards:
                    logger.debug(f"通过选择器 '{selector}' 找到 {len(cards)} 个视频卡片")
                    return cards
            except:
                continue
        return []

    def _extract_video_info(self, card):
        title = ""
        url = ""
        try:
            link_selectors = [
                ".bili-video-card__info--tit a",
                "a[href*='/video/']",
                "a",
            ]
            for sel in link_selectors:
                link_el = card.query_selector(sel)
                if link_el:
                    href = link_el.get_attribute("href") or ""
                    if "/video/" in href:
                        title = link_el.inner_text().strip() or link_el.get_attribute("title") or ""
                        url = href
                        break
            
            if not title:
                title_el = card.query_selector("[title]")
                if title_el:
                    title = title_el.get_attribute("title") or ""
            
            if not title:
                img_el = card.query_selector("img[alt]")
                if img_el:
                    title = img_el.get_attribute("alt") or ""
            
            if url and url.startswith("//"):
                url = "https:" + url
            elif url and not url.startswith("http"):
                url = "https://www.bilibili.com" + url
        except Exception as e:
            logger.debug(f"提取视频信息失败: {e}")
        
        return title, url

    def _click_refresh_button(self, page: Page):
        try:
            btn = page.query_selector("button.roll-btn")
            if btn:
                btn.click()
                logger.debug("已点击换一换按钮")
                self._interruptible_sleep(2)
            else:
                logger.debug("未找到换一换按钮")
        except Exception as e:
            logger.debug(f"点击换一换失败: {e}")

    def _get_video_duration(self, page: Page) -> int:
        """Get actual video duration in seconds from the page player"""
        try:
            duration = page.evaluate("""() => {
                // Method 1: Get from <video> element
                const video = document.querySelector('video');
                if (video && video.duration && isFinite(video.duration) && video.duration > 0) {
                    return Math.floor(video.duration);
                }
                // Method 2: Parse from player duration text (e.g. "03:25")
                const durationEl = document.querySelector('.bpx-player-ctrl-time-duration');
                if (durationEl) {
                    const text = durationEl.textContent.trim();
                    const parts = text.split(':').map(Number);
                    if (parts.length === 2) return parts[0] * 60 + parts[1];
                    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
                }
                return 0;
            }""")
            return duration if isinstance(duration, (int, float)) and duration > 0 else 0
        except Exception as e:
            logger.debug(f"获取视频时长失败: {e}")
            return 0

    def _watch_video(self, page: Page, url: str, title: str, status_callback):
        """Simulate watching a single video"""
        page.goto(url, wait_until="domcontentloaded")
        if self._interruptible_sleep(3): return
        if check_captcha_on_page(page):
            if not self._wait_captcha_resolved(page, page.url or url):
                return
            logger.info("验证码已解决，继续观看...")
        
        watch_min = self.warmup_config.get('behavior', {}).get('watch_time_min', 20)
        watch_max = self.warmup_config.get('behavior', {}).get('watch_time_max', 240)
        watch_duration = random.randint(watch_min, watch_max)
        
        # Get actual video duration and cap watch time
        actual_duration = self._get_video_duration(page)
        if actual_duration > 0:
            if watch_duration > actual_duration:
                logger.info(f"视频实际时长: {actual_duration} 秒，随机观看时长 {watch_duration} 秒超出，调整为 {actual_duration} 秒")
                watch_duration = actual_duration
            else:
                logger.info(f"视频实际时长: {actual_duration} 秒，将观看 {watch_duration} 秒")
        else:
            logger.info(f"无法获取视频实际时长，将观看 {watch_duration} 秒")
        
        start_watch_time = time.time()
        elapsed = 0
        
        behavior_conf = self.warmup_config.get('behavior', {})
        scroll_prob = behavior_conf.get('scroll_prob', 0.10)
        pause_prob = behavior_conf.get('pause_prob', 0.08)
        view_comment_prob = behavior_conf.get('view_comment_prob', 0.05)
        like_prob = behavior_conf.get('like_prob', 0.30)
        
        # Random like at the start of the video (one-time per video)
        if behavior_conf.get('random_like') and random.random() < like_prob:
            if self._like_video(page):
                self.like_count += 1
        
        while self.running and elapsed < watch_duration:
            if check_captcha_on_page(page):
                if not self._wait_captcha_resolved(page, page.url or url):
                    break
                logger.info("验证码已解决，继续观看...")
            # Update status periodically
            if status_callback:
                status_callback(
                    title, 
                    self.watched_count, 
                    round((self.total_time_seconds + elapsed) / 60, 1), 
                    self.like_count,
                    self.comment_count
                )
            
            # Random actions (independent checks, configurable probabilities)
            if random.random() < scroll_prob and behavior_conf.get('random_scroll'):
                scroll_amount = random.randint(300, 800)
                logger.info(f"[随机滚动] 滚动页面 {scroll_amount}px")
                page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                if self._interruptible_sleep(random.uniform(1, 3)): break
                if random.random() < 0.5:
                    page.evaluate(f"window.scrollBy(0, -{scroll_amount // 2})")
            
            if random.random() < pause_prob and behavior_conf.get('random_pause'):
                pause_duration = random.uniform(2, 5)
                logger.info(f"[随机暂停] 暂停播放 {pause_duration:.1f} 秒")
                page.keyboard.press("Space")
                if self._interruptible_sleep(pause_duration): break
                page.keyboard.press("Space")
                logger.info("[随机暂停] 恢复播放")
            
            if random.random() < view_comment_prob and behavior_conf.get('view_comment'):
                logger.info("[随机查看评论区] 滚动到评论区")
                page.evaluate("window.scrollTo(0, 1000)")
                if self._interruptible_sleep(random.uniform(3, 7)): break
                page.evaluate("window.scrollTo(0, 0)")
                if self._interruptible_sleep(random.uniform(1, 2)): break
            
            # Wait a bit before next action check
            sleep_time = min(5, watch_duration - elapsed)
            if self._interruptible_sleep(sleep_time): break
            elapsed = time.time() - start_watch_time
            
        self.total_time_seconds += time.time() - start_watch_time
        
        # Optional random comment
        comment_conf = self.warmup_config.get('comment', {})
        if self.running and comment_conf.get('enable') and random.random() < comment_conf.get('probability', 0.1):
            self._post_random_comment(page)

    def _like_video(self, page: Page) -> bool:
        """Click the like button on the current video"""
        try:
            liked = page.evaluate("""() => {
                // Check if already liked
                const likeBtn = document.querySelector('.video-like-info');
                if (likeBtn && likeBtn.classList.contains('on')) {
                    return 'already_liked';
                }
                // Try multiple selectors for the like button
                const selectors = [
                    '.video-like-info',
                    '.video-like',
                    '#arc_toolbar_report .video-like',
                    '[data-title="点赞"]',
                ];
                for (const sel of selectors) {
                    const btn = document.querySelector(sel);
                    if (btn) {
                        btn.click();
                        return 'ok';
                    }
                }
                return 'not_found';
            }""")
            if liked == 'ok':
                logger.info("[随机点赞] 已为视频点赞 👍")
                return True
            elif liked == 'already_liked':
                logger.info("[随机点赞] 视频已经点过赞，跳过")
                return False
            else:
                logger.debug(f"[随机点赞] 未找到点赞按钮: {liked}")
                return False
        except Exception as e:
            logger.debug(f"[随机点赞] 点赞失败: {e}")
            return False

    def _post_random_comment(self, page: Page):
        """Post a random comment from templates"""
        try:
            # This would reuse logic from CommentManager but simplified
            logger.info("触发随机评论...")
            # For now, just log it as we need to ensure we don't get banned
            # In a real implementation, we'd find the comment box and type a template
            # self.comment_count += 1
            pass
        except Exception as e:
            logger.error(f"随机评论失败: {e}")
