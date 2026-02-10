from playwright.sync_api import Page
from utils.logger import get_logger
import urllib.parse
import time

logger = get_logger()

class SearchManager:
    def __init__(self, page: Page):
        self.page = page

    def search_videos(self, keyword: str, max_count: int = 5, order: str = "pubdate", duration: int = 0) -> list[str]:
        """
        Search for videos and return a list of URLs.
        order: 'pubdate' (latest), 'click' (most view), 'totalrank' (default), 'dm', 'stow'
        duration: 0 (all), 1 (<10m), 2 (10-30m), 3 (30-60m), 4 (>60m)
        """
        logger.info(f"Searching for keyword: {keyword}, order: {order}, duration: {duration}")
        
        encoded_keyword = urllib.parse.quote(keyword)
        # Construct URL with all filters
        url = f"https://search.bilibili.com/all?keyword={encoded_keyword}&order={order}&duration={duration}"
        
        try:
            self.page.goto(url, wait_until="domcontentloaded")
            
            # Wait for list to load
            try:
                self.page.wait_for_selector(".video-list .bili-video-card, .bili-video-card", timeout=10000)
            except:
                logger.warning("Timeout waiting for video list selector. Page might handle captcha or empty.")
                return []
            
            video_urls = []
            
            # Scroll down a bit to trigger lazy load
            self.page.evaluate("window.scrollBy(0, 500)")
            time.sleep(1)
            
            # Locator for video cards
            cards = self.page.locator(".bili-video-card")
            count = cards.count()
            
            logger.debug(f"Found {count} potential video cards.")
            
            for i in range(count):
                if len(video_urls) >= max_count:
                    break
                    
                card = cards.nth(i)
                
                try:
                    # Look for the main link
                    link_locator = card.locator("a[href*='video/BV']").first
                    if link_locator.count() > 0:
                        href = link_locator.get_attribute("href")
                        if href:
                            if href.startswith("//"):
                                href = "https:" + href
                            
                            # Clean query params
                            if "?" in href:
                                href = href.split("?")[0]
                                
                            # Avoid duplicates in current batch
                            if href not in video_urls:
                                video_urls.append(href)
                except Exception as e:
                    pass
                    
            logger.info(f"Extracted {len(video_urls)} video URLs.")
            return video_urls
            
        except Exception as e:
            logger.error(f"Error searching videos: {e}")
            return []
