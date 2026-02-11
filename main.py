import time
import sys
import random
import threading
import csv
import os
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from core.auth import AuthManager
from core.search import SearchManager
from core.comment import CommentManager
from core.history import HistoryManager
from core.config import ConfigValidator
from core.warmup import WarmupManager
from utils.logger import get_logger
from utils.date_parser import parse_bilibili_date

logger = get_logger()

_stop_event = threading.Event()
_current_manager = None

def stop_task():
    global _current_manager
    _stop_event.set()
    if _current_manager:
        _current_manager.stop()
    logger.info("收到停止信号。")

def reset_stop_flag():
    global _current_manager
    _stop_event.clear()
    _current_manager = None

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

def get_browser_launch_args(config, force_headed=False):
    headless = config["behavior"].get("headless", False)
    if force_headed:
        headless = False
        
    browser_config = config.get("browser", {})
    executable_path = browser_config.get("path", "")
    debug_port = browser_config.get("port", 0)
    
    launch_args = {
        "headless": headless,
        "args": [
            "--no-sandbox",
            "--disable-infobars",
            "--window-size=1280,720",
            "--disable-blink-features=AutomationControlled",
            "--mute-audio"
        ]
    }
    
    if executable_path:
        executable_path = os.path.normpath(executable_path)

    if executable_path and os.path.exists(executable_path):
        launch_args["executable_path"] = executable_path
    elif getattr(sys, 'frozen', False):
        logger.error("在打包环境中运行，必须在配置中指定浏览器路径！")
        return None
        
    if debug_port > 0:
        launch_args["args"].append(f"--remote-debugging-port={debug_port}")
    
    return launch_args

def main(video_callback=None, status_callback=None):
    reset_stop_flag()
    
    try:
        config = ConfigValidator.load_config()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        return

    launch_args = get_browser_launch_args(config)
    if not launch_args: return

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(**launch_args)
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            return
            
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
        target_count = config["search"]["max_videos_per_keyword"]
        total_success = 0
        
        for keyword in keywords:
            if _stop_event.is_set(): break
            if total_success >= target_count: break
            logger.info(f"正在处理关键词: {keyword}")
            is_first_page = True
            
            while total_success < target_count and not _stop_event.is_set():
                strategy_config = config["search"].get("strategy", {})
                selection_mode = strategy_config.get("selection", "order")
                strict_match = strategy_config.get("strict_title_match", False)
                filter_config = config["search"].get("filter", {})
                
                if is_first_page:
                    videos = search_mgr.search_videos(
                        keyword, 
                        max_count=1000,
                        order=filter_config.get("sort", "totalrank"),
                        duration=filter_config.get("duration", 0),
                        time_range=filter_config.get("time_range")
                    )
                    is_first_page = False
                else:
                    videos = search_mgr.get_current_page_videos(max_count=1000)
                
                if not videos: break
                
                candidate_videos = []
                for v in videos:
                    if history_mgr.has(v['bv']): continue
                    if strict_match and keyword.lower() not in v.get('title', '').lower(): continue
                    
                    time_filter = filter_config.get("time_range", {})
                    t_type = time_filter.get("type", "none")
                    if t_type != "none":
                        v_date = parse_bilibili_date(v.get('date', ''))
                        if not v_date: continue
                        if t_type == "recent":
                            if v_date < datetime.now() - timedelta(days=time_filter.get("value", 1)): continue
                        elif t_type == "range":
                            val = time_filter.get("value", {})
                            try:
                                s_date = datetime.strptime(val.get("start"), "%Y-%m-%d")
                                e_date = datetime.strptime(val.get("end"), "%Y-%m-%d") + timedelta(days=1)
                                if not (s_date <= v_date < e_date): continue
                            except: continue
                    candidate_videos.append(v)
                
                if candidate_videos:
                    if selection_mode == "random": random.shuffle(candidate_videos)
                    for video_info in candidate_videos:
                        if _stop_event.is_set() or total_success >= target_count: break
                        if video_callback: video_callback(video_info)
                        if status_callback: status_callback(video_info['bv'], "处理中...")
                        
                        text = random.choice(config["comment"]["texts"])
                        image_path = None
                        if config["comment"].get("enable_image", False) and config["comment"].get("images"):
                            image_path = random.choice(config["comment"]["images"])
                        
                        success = comment_mgr.post_comment(video_info['url'], text, image_path)
                        status = "成功" if success else "失败"
                        log_comment_result(video_info, status, text)
                        if status_callback: status_callback(video_info['bv'], status)
                        
                        if success:
                            history_mgr.add(video_info['bv'])
                            total_success += 1
                        
                        time.sleep(random.uniform(config["behavior"].get("min_delay", 5), config["behavior"].get("max_delay", 15)))
                
                if total_success >= target_count or not search_mgr.go_to_next_page(): break
            
        logger.info(f"所有任务已完成。本次成功评论: {total_success}/{target_count}")
        browser.close()

def run_warmup(status_callback=None):
    global _current_manager
    reset_stop_flag()
    
    try:
        config = ConfigValidator.load_config()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        return

    launch_args = get_browser_launch_args(config, force_headed=True)
    if not launch_args: return

    logger.info("养号模式强制使用有头浏览器（已静音）")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(**launch_args)
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            return
            
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

        _current_manager = WarmupManager(context, config)
        _current_manager.run(status_callback=status_callback)
        
        browser.close()

if __name__ == "__main__":
    main()
