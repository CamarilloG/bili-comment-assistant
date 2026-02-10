from playwright.sync_api import Page
from utils.logger import get_logger
from core.selectors import BilibiliSelectors
from utils.retry import retry
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import urllib.parse
import time

logger = get_logger()

class SearchManager:
    def __init__(self, page: Page):
        self.page = page

    @retry(max_attempts=2, delay=2.0, exceptions=(PlaywrightTimeoutError, Exception))
    def search_videos(self, keyword: str, max_count: int = 5, order: str = "pubdate", duration: int = 0, time_range: dict = None) -> list[dict]:
        """
        Navigate to search page and return videos from the first page.
        """
        logger.info(f"搜索关键词: {keyword}, 排序: {order}, 时长: {duration}")
        
        encoded_keyword = urllib.parse.quote(keyword)
        url = f"https://search.bilibili.com/video?keyword={encoded_keyword}&order={order}&duration={duration}"
        
        # Append URL Date Filters if present
        if time_range and time_range.get("type") != "none":
            try:
                import time
                from datetime import datetime, timedelta
                
                now = datetime.now()
                begin_ts = 0
                end_ts = int(now.timestamp()) # Default end is now
                
                t_type = time_range.get("type")
                if t_type == "recent":
                    days = time_filter_val = time_range.get("value", 1)
                    # Begin = Now - X days
                    # End = Now
                    begin_dt = now - timedelta(days=days)
                    begin_ts = int(begin_dt.timestamp())
                    
                elif t_type == "range":
                    val = time_range.get("value", {})
                    start_str = val.get("start")
                    end_str = val.get("end")
                    if start_str and end_str:
                        # Parse YYYY-MM-DD
                        s_dt = datetime.strptime(start_str, "%Y-%m-%d")
                        # End date usually implies end of that day? Or just 00:00?
                        # Bilibili likely uses seconds. Let's set end to 23:59:59 of end date
                        e_dt = datetime.strptime(end_str, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
                        begin_ts = int(s_dt.timestamp())
                        end_ts = int(e_dt.timestamp())
                
                if begin_ts > 0:
                    url += f"&pubtime_begin_s={begin_ts}&pubtime_end_s={end_ts}"
                    logger.info(f"应用 URL 时间筛选: {begin_ts} - {end_ts}")
            except Exception as e:
                logger.error(f"构造时间筛选 URL 出错: {e}")
        
        try:
            self.page.goto(url, wait_until="domcontentloaded")
            return self.get_current_page_videos(max_count)
        except Exception as e:
            logger.error(f"搜索导航出错: {e}")
            return []

    # Removed apply_time_filter as we use URL params now
    
    def get_current_page_videos(self, max_count: int = 20) -> list[dict]:
        """
        Extract videos from the current page content.
        """
        try:
            selectors = BilibiliSelectors.SEARCH
            try:
                self.page.wait_for_selector(selectors["video_card"], timeout=10000)
            except:
                logger.warning("等待视频列表选择器超时。")
                if self.page.locator(".search-no-result").count() > 0:
                    logger.info("当前页面无结果。")
                    return []
            
            video_list = []
            cards = self.page.locator(selectors["video_card"])
            count = cards.count()
            logger.debug(f"当前页找到 {count} 个视频卡片。")
            
            # Use a very high limit for the loop to ensure we check all cards
            # The 'max_count' parameter will still limit the returned list size
            # But if the user passes a huge max_count, we want to get everything.
            loop_limit = count 
            
            for i in range(loop_limit): 
                try:
                    card = cards.nth(i)
                    link_el = card.locator(selectors["link"]).first
                    if link_el.count() == 0: continue
                        
                    url = link_el.get_attribute("href")
                    if not url: continue
                    if not url.startswith("http"): url = "https:" + url
                    url = url.split("?")[0]
                    
                    bv = ""
                    if "/video/" in url:
                        parts = url.split("/video/")
                        if len(parts) > 1: bv = parts[1].split("/")[0]
                    
                    title = "Unknown"
                    if card.locator(selectors["title"]).count() > 0:
                        title = card.locator(selectors["title"]).first.inner_text().strip()
                        
                    author = "Unknown"
                    if card.locator(selectors["author"]).count() > 0:
                        author = card.locator(selectors["author"]).first.inner_text().strip()
                        
                    date = ""
                    if card.locator(selectors["date"]).count() > 0:
                        date = card.locator(selectors["date"]).first.inner_text().strip()
                        
                    views = "0"
                    comments = "0"
                    stats = card.locator(selectors["stats"])
                    if stats.count() > 0: views = stats.nth(0).inner_text().strip()
                    if stats.count() > 1: comments = stats.nth(1).inner_text().strip()
                    
                    video_info = {
                        "url": url, "bv": bv, "title": title, "author": author,
                        "date": date, "views": views, "comments": comments
                    }
                    
                    if not any(v['bv'] == bv for v in video_list if v['bv']):
                        video_list.append(video_info)
                        if len(video_list) >= max_count: break
                            
                except Exception as e:
                    continue
                    
            logger.info(f"从当前页提取了 {len(video_list)} 个视频。")
            return video_list
            
        except Exception as e:
            logger.error(f"提取视频信息出错: {e}")
            return []

    def go_to_next_page(self) -> bool:
        """
        Attempt to click 'Next Page'. Returns True if successful.
        """
        try:
            logger.info("尝试翻页...")
            next_btn = self.page.locator(BilibiliSelectors.SEARCH["next_page"]).first
            
            if next_btn.count() > 0 and next_btn.is_visible() and next_btn.is_enabled():
                # Check if it has 'disabled' class (sometimes handled by class not attribute)
                if "disabled" in next_btn.get_attribute("class") or "":
                    logger.info("下一页按钮被禁用 (已达末页)。")
                    return False
                    
                # Get current first video title/BV to verify change later (optional, skipping for speed)
                next_btn.click()
                self.page.wait_for_timeout(2000) # Wait for reload
                return True
            else:
                logger.info("未找到下一页按钮或已达末页。")
                return False
        except Exception as e:
            logger.error(f"翻页失败: {e}")
            return False
