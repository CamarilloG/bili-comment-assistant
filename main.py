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
from utils.date_parser import parse_bilibili_date
from datetime import datetime, timedelta

logger = get_logger()

_stop_event = threading.Event()

def stop_task():
    _stop_event.set()
    logger.info("收到停止信号。")

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
    
    logger.info("启动 Bilibili 机器人...")
    
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
        logger.info(f"使用自定义浏览器: {executable_path}")
        
    if debug_port > 0:
        launch_args["args"].append(f"--remote-debugging-port={debug_port}")
        logger.info(f"使用远程调试端口: {debug_port}")
    
    with sync_playwright() as p:
        # Launch browser
        try:
            browser = p.chromium.launch(**launch_args)
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            return
            
        # Create context
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        auth = AuthManager(context, config["account"]["cookie_file"])
        
        if not auth.login():
            logger.error("登录失败。正在退出。")
            browser.close()
            return

        search_page = context.new_page()
        comment_page = context.new_page()
        
        search_mgr = SearchManager(search_page)
        comment_mgr = CommentManager(comment_page)
        history_mgr = HistoryManager()
        
        keywords = config["search"]["keywords"]
        total_success = 0
        
        # We treat max_videos_per_keyword as the TOTAL session target in this context based on user feedback
        # Or at least per keyword. User said "Run Parameter Max Comment Count".
        # Let's stick to per keyword to be safe, or if there is only 1 keyword it is the same.
        # But to support "fill up to N", we need a loop.
        
        target_count = config["search"]["max_videos_per_keyword"]
        
        # Pagination / Continuation Logic
        # We need to restructure the loop to handle pagination PER KEYWORD
        for keyword in keywords:
            if _stop_event.is_set(): break
            if total_success >= target_count: break
                
            logger.info(f"正在处理关键词: {keyword}")
            
            # Reset page context for new keyword
            is_first_page = True
            
            while total_success < target_count and not _stop_event.is_set():
                strategy_config = config["search"].get("strategy", {})
                selection_mode = strategy_config.get("selection", "order")
                strict_match = strategy_config.get("strict_title_match", False)
                filter_config = config["search"].get("filter", {})
                
                fetch_multiplier = 3
                # Removed max() limit to fetch ALL videos from page as requested
                # fetch_count = max(20, target_count * fetch_multiplier)
                # Pass a very large number to search_videos/get_current_page_videos
                # search.py logic handles the actual loop limit based on card count
                fetch_count = 1000 
                
                if is_first_page:
                    # Initial Search (Navigates)
                    videos = search_mgr.search_videos(
                        keyword, 
                        max_count=fetch_count,
                        order=filter_config.get("sort", "totalrank"),
                        duration=filter_config.get("duration", 0),
                        time_range=filter_config.get("time_range")
                    )
                    
                    is_first_page = False
                else:
                    # Just scrape current page (Already navigated via Next Page)
                    videos = search_mgr.get_current_page_videos(max_count=fetch_count)
                
                if not videos:
                    logger.warning(f"当前页未提取到视频。")
                    # Try next page anyway? Or stop?
                    # If empty, maybe captcha or end.
                    pass
                
                # Filter Candidates
                candidate_videos = []
                for v in videos:
                    # ... (Filter Logic Same as Before) ...
                    # 1. History Check
                    if history_mgr.has(v['bv']):
                        logger.debug(f"跳过已访问的视频: {v['bv']}")
                        continue
                    
                    # 2. Strict Title Match
                    if strict_match:
                        if keyword.lower() not in v.get('title', '').lower():
                            logger.info(f"标题不匹配 (严格模式): {v.get('title')} - 跳过")
                            continue
                    
                    # 3. Date Filter
                    time_filter = filter_config.get("time_range", {})
                    t_type = time_filter.get("type", "none")
                    
                    if t_type != "none":
                        date_str = v.get('date', '')
                        if not date_str:
                            logger.warning(f"无法获取日期，跳过: {v['bv']}")
                            continue
                            
                        v_date = parse_bilibili_date(date_str)
                        if not v_date:
                            logger.warning(f"日期解析失败: {date_str}, 跳过")
                            continue
                        
                        if t_type == "recent":
                            days = time_filter.get("value", 1)
                            cutoff = datetime.now() - timedelta(days=days)
                            if v_date < cutoff:
                                logger.info(f"日期不满足 (最近 {days} 天): {date_str} - 跳过")
                                continue
                                
                        elif t_type == "range":
                            val = time_filter.get("value", {})
                            start_str = val.get("start")
                            end_str = val.get("end")
                            if start_str and end_str:
                                try:
                                    s_date = datetime.strptime(start_str, "%Y-%m-%d")
                                    e_date = datetime.strptime(end_str, "%Y-%m-%d") + timedelta(days=1)
                                    if not (s_date <= v_date < e_date):
                                        logger.info(f"日期不满足范围 ({start_str} - {end_str}): {date_str} - 跳过")
                                        continue
                                except Exception as e:
                                    logger.error(f"日期范围比较出错: {e}")
                                    continue
    
                    candidate_videos.append(v)
                
                logger.info(f"关键词 '{keyword}' 当前页有效候选: {len(candidate_videos)} 个")
                
                # Comment Loop
                if candidate_videos:
                    if selection_mode == "random":
                        random.shuffle(candidate_videos)
                        
                    for video_info in candidate_videos:
                        if _stop_event.is_set(): break
                        if total_success >= target_count: break
                        
                        # ... (Comment Logic Same as Before) ...
                        if video_callback: video_callback(video_info)
                        url = video_info['url']; bv = video_info['bv']
                        text = random.choice(config["comment"]["texts"])
                        image_path = None
                        if config["comment"].get("enable_image", False) and config["comment"].get("images"):
                            image_path = random.choice(config["comment"]["images"])
                        
                        if status_callback: status_callback(bv, "处理中...")
                        success = comment_mgr.post_comment(url, text, image_path)
                        status = "成功" if success else "失败"
                        log_comment_result(video_info, status, text)
                        if status_callback: status_callback(bv, status)
                        
                        if success:
                            history_mgr.add(bv)
                            logger.info(f"评论发布成功: {bv}")
                            total_success += 1
                        else:
                            logger.warning(f"评论发布失败: {bv}")
                        
                        delay = random.uniform(min_delay, max_delay)
                        logger.info(f"休眠 {delay:.2f} 秒...")
                        time.sleep(delay)
                
                # Check if we need more
                if total_success >= target_count:
                    break
                
                # Try Next Page
                if not search_mgr.go_to_next_page():
                    logger.info("翻页失败或已达末页。停止当前关键词搜索。")
                    break # Break inner while loop, go to next keyword
                
                # If next page success, loop continues (is_first_page=False)
            
        logger.info(f"所有任务已完成。本次成功评论: {total_success}/{target_count}")
        browser.close()

if __name__ == "__main__":
    main()
