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
    def search_videos(self, keyword: str, max_count: int = 5, order: str = "pubdate", duration: int = 0) -> list[str]:
        """
        Search for videos and return a list of URLs.
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
                selectors = BilibiliSelectors.get_search_video_cards()
                self.page.wait_for_selector(selectors, timeout=10000)
            except:
                logger.warning("Timeout waiting for video list selector. Page might handle captcha or empty.")
                # Maybe empty result?
                if self.page.locator(".search-no-result").count() > 0:
                    logger.info("Search returned no results.")
                    return []
                # Don't return empty yet, try to find anyway
            
            # Extract URLs
            video_urls = []
            cards = self.page.locator(selectors)
            count = cards.count()
            logger.debug(f"Found {count} potential video cards.")
            
            for i in range(min(count, max_count * 3)): # Check more cards to filter valid ones
                try:
                    card = cards.nth(i)
                    # Use link selector
                    link_selector = BilibiliSelectors.get_search_video_link()
                    if card.locator(link_selector).count() > 0:
                        url = card.locator(link_selector).first.get_attribute("href")
                        if url:
                            if not url.startswith("http"):
                                url = "https:" + url
                            # Clean URL
                            url = url.split("?")[0]
                            if url not in video_urls:
                                video_urls.append(url)
                                if len(video_urls) >= max_count:
                                    break
                except Exception as e:
                    continue
                    
            logger.info(f"Extracted {len(video_urls)} video URLs.")
            return video_urls
            
        except Exception as e:
            logger.error(f"Error searching videos: {e}")
            return []
