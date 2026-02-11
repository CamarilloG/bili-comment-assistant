import time
import random
from loguru import logger
from playwright.sync_api import Page, BrowserContext

class WarmupManager:
    def __init__(self, context: BrowserContext, config: dict):
        self.context = context
        self.config = config
        self.warmup_config = config.get('warmup', {})
        self.running = True
        
        # Stats
        self.watched_count = 0
        self.total_time_seconds = 0
        self.comment_count = 0

    def stop(self):
        self.running = False

    def run(self, status_callback=None):
        """Main loop for warmup task"""
        duration_minutes = self.warmup_config.get('basic', {}).get('duration_minutes', 30)
        max_videos = self.warmup_config.get('basic', {}).get('max_videos', 20)
        end_time = time.time() + (duration_minutes * 60)
        
        logger.info(f"开始养号任务，预计时长: {duration_minutes} 分钟，目标视频数: {max_videos}")
        
        page = self.context.new_page()
        
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
                
                video_cards = self._wait_for_video_cards(page)
                
                if not video_cards:
                    logger.warning("未能在首页找到推荐视频，尝试滚动页面...")
                    page.evaluate("window.scrollBy(0, 600)")
                    time.sleep(3)
                    video_cards = self._wait_for_video_cards(page)
                
                if not video_cards:
                    logger.warning("仍未找到视频，尝试点击换一换...")
                    self._click_refresh_button(page)
                    time.sleep(3)
                    video_cards = self._wait_for_video_cards(page)
                
                if not video_cards:
                    logger.error("多次尝试后仍未找到推荐视频，等待后重试...")
                    time.sleep(10)
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
                        self.comment_count
                    )
                
                delay = random.uniform(3, 10)
                logger.info(f"视频观看结束，随机等待 {delay:.1f} 秒...")
                time.sleep(delay)
                
        except Exception as e:
            logger.error(f"养号过程中发生错误: {e}")
        finally:
            page.close()
            logger.info(f"养号任务结束。共观看 {self.watched_count} 个视频，累计时长 {self.total_time_seconds / 60:.1f} 分钟。")

    def _wait_for_video_cards(self, page: Page, timeout=15000):
        selectors = [
            ".bili-video-card",
            ".feed-card",
            ".recommended-container_det498 .video-card",
        ]
        for selector in selectors:
            try:
                page.wait_for_selector(selector, timeout=timeout)
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
                time.sleep(2)
            else:
                logger.debug("未找到换一换按钮")
        except Exception as e:
            logger.debug(f"点击换一换失败: {e}")

    def _watch_video(self, page: Page, url: str, title: str, status_callback):
        """Simulate watching a single video"""
        page.goto(url, wait_until="domcontentloaded")
        time.sleep(3)
        
        watch_min = self.warmup_config.get('behavior', {}).get('watch_time_min', 20)
        watch_max = self.warmup_config.get('behavior', {}).get('watch_time_max', 240)
        watch_duration = random.randint(watch_min, watch_max)
        
        logger.info(f"准备观看视频 {watch_duration} 秒...")
        
        start_watch_time = time.time()
        elapsed = 0
        
        behavior_conf = self.warmup_config.get('behavior', {})
        
        while self.running and elapsed < watch_duration:
            # Update status periodically
            if status_callback:
                status_callback(
                    title, 
                    self.watched_count, 
                    round((self.total_time_seconds + elapsed) / 60, 1), 
                    self.comment_count
                )
            
            # Random actions
            action_roll = random.random()
            
            if action_roll < 0.1 and behavior_conf.get('random_scroll'):
                # Scroll down to see comments or recommendations
                scroll_amount = random.randint(300, 800)
                logger.debug(f"随机滚动页面: {scroll_amount}px")
                page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                time.sleep(random.uniform(1, 3))
                if random.random() < 0.5: # Scroll back up sometimes
                    page.evaluate(f"window.scrollBy(0, -{scroll_amount//2})")
            
            elif action_roll < 0.15 and behavior_conf.get('random_pause'):
                # Pause/Resume video
                logger.debug("随机暂停/恢复播放")
                page.keyboard.press("Space")
                time.sleep(random.uniform(2, 5))
                page.keyboard.press("Space")
            
            elif action_roll < 0.05 and behavior_conf.get('view_comment'):
                # Scroll to comment area
                logger.debug("尝试查看评论区")
                page.evaluate("window.scrollTo(0, 1000)")
                time.sleep(random.uniform(3, 7))
            
            # Wait a bit before next check
            sleep_time = min(5, watch_duration - elapsed)
            time.sleep(sleep_time)
            elapsed = time.time() - start_watch_time
            
        self.total_time_seconds += elapsed
        
        # 4. Optional random comment
        comment_conf = self.warmup_config.get('comment', {})
        if self.running and comment_conf.get('enable') and random.random() < comment_conf.get('probability', 0.1):
            self._post_random_comment(page)

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
