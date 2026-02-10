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
    def search_videos(self, keyword: str, max_count: int = 5, order: str = "pubdate", duration: int = 0) -> list[dict]:
        """
        Search for videos and return a list of video info dicts.
        order: 'pubdate' (latest), 'click' (most view), 'totalrank' (default), 'dm', 'stow'
        duration: 0 (all), 1 (<10m), 2 (10-30m), 3 (30-60m), 4 (>60m)
        """
        logger.info(f"Searching for keyword: {keyword}, order: {order}, duration: {duration}")
        
        encoded_keyword = urllib.parse.quote(keyword)
        # Construct URL with all filters
        # Use video search interface to support sorting and filtering correctly
        url = f"https://search.bilibili.com/video?keyword={encoded_keyword}&order={order}&duration={duration}"
        
        try:
            self.page.goto(url, wait_until="domcontentloaded")
            
            # Wait for list to load
            try:
                # Use selector from centralized class
                selectors = BilibiliSelectors.SEARCH
                self.page.wait_for_selector(selectors["video_card"], timeout=10000)
            except:
                logger.warning("Timeout waiting for video list selector. Page might handle captcha or empty.")
                # Maybe empty result?
                if self.page.locator(".search-no-result").count() > 0:
                    logger.info("Search returned no results.")
                    return []
                # Don't return empty yet, try to find anyway
            
            # Extract Video Info
            video_list = []
            cards = self.page.locator(selectors["video_card"])
            count = cards.count()
            logger.debug(f"Found {count} potential video cards.")
            
            for i in range(min(count, max_count * 3)): # Check more cards to filter valid ones
                try:
                    card = cards.nth(i)
                    # Use link selector
                    link_el = card.locator(selectors["link"]).first
                    if link_el.count() == 0:
                        continue
                        
                    url = link_el.get_attribute("href")
                    if not url: continue
                    if not url.startswith("http"):
                        url = "https:" + url
                    # Clean URL
                    url = url.split("?")[0]
                    
                    # Extract BV from URL
                    bv = ""
                    if "/video/" in url:
                        parts = url.split("/video/")
                        if len(parts) > 1:
                            bv = parts[1].split("/")[0]
                    
                    # Extract Metadata
                    title = "Unknown"
                    if card.locator(selectors["title"]).count() > 0:
                        title = card.locator(selectors["title"]).first.inner_text().strip()
                        
                    author = "Unknown"
                    if card.locator(selectors["author"]).count() > 0:
                        author = card.locator(selectors["author"]).first.inner_text().strip()
                        
                    date = ""
                    if card.locator(selectors["date"]).count() > 0:
                        date = card.locator(selectors["date"]).first.inner_text().strip()
                        
                    # Stats (Views, Comments, etc.)
                    views = "0"
                    comments = "0"
                    stats = card.locator(selectors["stats"])
                    if stats.count() > 0:
                        views = stats.nth(0).inner_text().strip()
                    if stats.count() > 1:
                        comments = stats.nth(1).inner_text().strip()
                    
                    video_info = {
                        "url": url,
                        "bv": bv,
                        "title": title,
                        "author": author,
                        "date": date,
                        "views": views,
                        "comments": comments
                    }
                    
                    # Check for duplicates
                    if not any(v['bv'] == bv for v in video_list if v['bv']):
                        video_list.append(video_info)
                        if len(video_list) >= max_count:
                            break
                            
                except Exception as e:
                    logger.warning(f"Error extracting video info: {e}")
                    continue
                    
            logger.info(f"Extracted {len(video_list)} videos.")
            return video_list
            
        except Exception as e:
            logger.error(f"Error searching videos: {e}")
            return []
