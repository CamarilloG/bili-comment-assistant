import time
import random
import threading
import csv
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from core.auth import AuthManager
from core.search import SearchManager
from core.comment import CommentManager
from core.history import HistoryManager
from core.config import ConfigValidator
from utils.logger import get_logger

logger = get_logger()

_stop_event = threading.Event()

def stop_task():
    _stop_event.set()
    logger.info("Stop signal received.")

def reset_stop_flag():
    _stop_event.clear()

def log_comment_result(video_info, status, comment_text):
    """Log comment result to CSV"""
    file_exists = os.path.isfile('comment_log.csv')
    try:
        with open('comment_log.csv', 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Time', 'BV', 'Title', 'Author', 'Status', 'Comment'])
            
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                video_info.get('bv', ''),
                video_info.get('title', ''),
                video_info.get('author', ''),
                status,
                comment_text
            ])
    except Exception as e:
        logger.error(f"Failed to write to log file: {e}")

def main(video_callback=None, status_callback=None):
    reset_stop_flag()
    
    try:
        config = ConfigValidator.load_config()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        return

    headless = config["behavior"].get("headless", False)
    min_delay = config["behavior"].get("min_delay", 5)
    max_delay = config["behavior"].get("max_delay", 15)
    
    # Browser Config
    browser_config = config.get("browser", {})
    executable_path = browser_config.get("path", "")
    debug_port = browser_config.get("port", 0)
    
    logger.info("Starting Bilibili Bot...")
    
    # Browser launch options
    launch_args = {
        "headless": headless,
        "args": [
            "--no-sandbox",
            "--disable-infobars",
            "--window-size=1280,720",
            "--disable-blink-features=AutomationControlled"
        ]
    }
    
    if executable_path and os.path.exists(executable_path):
        launch_args["executable_path"] = executable_path
        logger.info(f"Using custom browser: {executable_path}")
        
    if debug_port > 0:
        launch_args["args"].append(f"--remote-debugging-port={debug_port}")
        logger.info(f"Using remote debugging port: {debug_port}")
    
    with sync_playwright() as p:
        # Launch browser
        try:
            browser = p.chromium.launch(**launch_args)
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            return
            
        # Create context
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        auth = AuthManager(context, config["account"]["cookie_file"])
        
        if not auth.login():
            logger.error("Login failed. Exiting.")
            browser.close()
            return

        search_page = context.new_page()
        comment_page = context.new_page()
        
        search_mgr = SearchManager(search_page)
        comment_mgr = CommentManager(comment_page)
        history_mgr = HistoryManager()
        
        keywords = config["search"]["keywords"]
        for keyword in keywords:
            if _stop_event.is_set(): break
                
            logger.info(f"Processing keyword: {keyword}")
            
            strategy_config = config["search"].get("strategy", {})
            selection_mode = strategy_config.get("selection", "order")
            pool_size = strategy_config.get("random_pool_size", 20)
            target_count = config["search"]["max_videos_per_keyword"]
            
            fetch_count = pool_size if selection_mode == "random" else target_count
            
            filter_config = config["search"].get("filter", {})
            videos = search_mgr.search_videos(
                keyword, 
                max_count=fetch_count,
                order=filter_config.get("sort", "totalrank"),
                duration=filter_config.get("duration", 0)
            )
            
            if not videos:
                logger.warning(f"No videos found for keyword: {keyword}")
                continue
            
            # Selection Strategy
            if selection_mode == "random":
                if len(videos) > target_count:
                    selected_videos = random.sample(videos, target_count)
                else:
                    selected_videos = videos
            else:
                selected_videos = videos[:target_count]
            
            for video_info in selected_videos:
                if _stop_event.is_set(): break
                
                # Send data to GUI
                if video_callback:
                    video_callback(video_info)
                    
                url = video_info['url']
                bv = video_info['bv']
                
                if history_mgr.has(bv):
                    logger.info(f"Skipping already visited video: {bv}")
                    if status_callback:
                        status_callback(bv, "Skipped")
                    continue
                
                text = random.choice(config["comment"]["texts"])
                
                image_path = None
                if config["comment"].get("enable_image", False) and config["comment"].get("images"):
                    image_path = random.choice(config["comment"]["images"])
                
                if status_callback:
                    status_callback(bv, "Processing...")
                
                success = comment_mgr.post_comment(url, text, image_path)
                
                status = "Success" if success else "Failed"
                log_comment_result(video_info, status, text)
                
                if status_callback:
                    status_callback(bv, status)
                
                if success:
                    history_mgr.add(bv)
                    logger.info(f"Comment posted on {bv}")
                else:
                    logger.warning(f"Failed to comment on {bv}")
                
                delay = random.uniform(min_delay, max_delay)
                logger.info(f"Sleeping for {delay:.2f} seconds...")
                time.sleep(delay)
                
        logger.info("All tasks completed.")
        browser.close()

if __name__ == "__main__":
    main()
