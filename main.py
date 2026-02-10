import yaml
import time
import random
import os
from playwright.sync_api import sync_playwright
from core.auth import AuthManager
from core.search import SearchManager
from core.comment import CommentManager
from core.history import HistoryManager
from utils.logger import get_logger

logger = get_logger()

def load_config(path="config.yaml"):
    if not os.path.exists(path):
        logger.error(f"Config file {path} not found!")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    config = load_config()
    if not config:
        return

    headless = config["behavior"].get("headless", False)
    min_delay = config["behavior"].get("min_delay", 5)
    max_delay = config["behavior"].get("max_delay", 15)
    
    logger.info("Starting Bilibili Bot...")
    
    with sync_playwright() as p:
        # Launch browser
        # args=['--disable-blink-features=AutomationControlled'] helps avoid detection
        browser = p.chromium.launch(
            headless=headless, 
            args=['--disable-blink-features=AutomationControlled'] 
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Add stealth scripts if needed (basic stealth by modifying navigator.webdriver)
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Managers
        auth = AuthManager(context, config["account"]["cookie_file"])
        
        # Login
        if not auth.login():
            logger.error("Login failed. Exiting.")
            return

        # Use the same context for operations
        page = context.new_page()
        search_mgr = SearchManager(page)
        comment_mgr = CommentManager(page)
        history_mgr = HistoryManager()
        
        # Iterate Keywords
        keywords = config["search"]["keywords"]
        for keyword in keywords:
            logger.info(f"Processing keyword: {keyword}")
            
            # Determine selection strategy
            strategy_config = config["search"].get("strategy", {})
            selection_mode = strategy_config.get("selection", "order") # 'order' or 'random'
            pool_size = strategy_config.get("random_pool_size", 20)
            
            target_count = config["search"]["max_videos_per_keyword"]
            
            # If random mode, we need to fetch more videos first
            fetch_count = pool_size if selection_mode == "random" else target_count
            
            # Search
            filter_config = config["search"].get("filter", {})
            videos = search_mgr.search_videos(
                keyword, 
                max_count=fetch_count,
                order=filter_config.get("sort", "totalrank"), # default changed to totalrank in gui, keep compatible
                duration=filter_config.get("duration", 0)
            )
            
            if not videos:
                logger.warning(f"No videos found for keyword: {keyword}")
                continue
            
            # Apply Strategy
            if selection_mode == "random":
                if len(videos) > target_count:
                    logger.info(f"Randomly selecting {target_count} videos from pool of {len(videos)}...")
                    selected_videos = random.sample(videos, target_count)
                else:
                    selected_videos = videos
            else:
                # Sequential (already limited by search max_count if we passed it correctly, but search_mgr limits extraction)
                # Actually search_mgr limits extraction based on max_count.
                # If we passed fetch_count, we have fetch_count videos.
                # For sequential, we just take the first target_count.
                selected_videos = videos[:target_count]
            
            for video_url in selected_videos:
                bvid = history_mgr.extract_bvid(video_url)
                
                if history_mgr.has(bvid):
                    logger.info(f"Skipping already visited video: {bvid}")
                    continue
                
                # Select random comment
                text = random.choice(config["comment"]["texts"])
                
                # Select random image (optional)
                image_path = None
                if config["comment"].get("images"):
                    image_path = random.choice(config["comment"]["images"])
                
                # Post
                # Use a fresh page or existing page? 
                # CommentManager uses self.page. If we reuse it, we navigate away.
                # SearchManager also uses self.page.
                # If we navigate, we lose search results?
                # Actually, search_mgr extracts all URLs first, so it's fine to navigate away on the same page.
                
                success = comment_mgr.post_comment(video_url, text, image_path)
                
                if success:
                    history_mgr.add(bvid)
                    logger.info(f"Comment posted on {bvid}")
                else:
                    logger.warning(f"Failed to comment on {bvid}")
                
                # Delay
                delay = random.uniform(min_delay, max_delay)
                logger.info(f"Sleeping for {delay:.2f} seconds...")
                time.sleep(delay)
                
        logger.info("All tasks completed.")
        browser.close()

if __name__ == "__main__":
    main()
