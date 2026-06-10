import time
import sys
import random
import threading
import csv
import os
import json
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, Error as PlaywrightError
from core.auth import AuthManager
from core.search import SearchManager
from core.comment import CommentManager
from core.history import HistoryManager
from core.config import ConfigValidator
from core.warmup import WarmupManager
from core.ai_manager import AIManager
from core.captcha_tracker import CaptchaTracker
from core.notifier import CaptchaNotifier
from core.notification_manager import get_notification_manager
from utils.logger import get_logger
from utils.date_parser import parse_bilibili_date
from core.context import context as global_context
from core.slot import get_workdir, get_config_path, get_cookie_path, get_comment_log_path, get_qrcode_path, ensure_slot_dir
from utils.logger import slot_id_ctx

logger = get_logger()

# 全局重试计数器
_retry_counts = {}
MAX_CONSECUTIVE_FAILURES = 5

_slot_stop_events = {}
_slot_managers = {}
_slot_lock = threading.Lock()
_server_started = False


def check_retry_limit(slot_id: str, operation: str) -> bool:
    """检查是否超过重试上限"""
    key = f"{slot_id}:{operation}"
    count = _retry_counts.get(key, 0)

    if count >= MAX_CONSECUTIVE_FAILURES:
        logger.error(f"操作 {operation} 连续失败 {count} 次，停止重试")
        return False

    _retry_counts[key] = count + 1
    return True


def reset_retry_count(slot_id: str, operation: str):
    """成功后重置计数"""
    key = f"{slot_id}:{operation}"
    _retry_counts[key] = 0


def is_browser_connected(browser) -> bool:
    """检查浏览器是否仍然连接"""
    try:
        _ = browser.contexts
        return True
    except Exception:
        return False


def interruptible_wait(stop_event, seconds: float) -> bool:
    """可中断的等待，返回 True 表示被中断"""
    elapsed = 0
    while elapsed < seconds:
        if stop_event.wait(min(1, seconds - elapsed)):
            return True  # 被中断
        elapsed += 1
    return False  # 正常完成

def start_api_server():
    global _server_started
    if _server_started:
        return
    try:
        # Lazy import to avoid requiring FastAPI when only running GUI/local tasks
        from server.api import start_server
    except Exception as e:
        logger.error(f"Failed to import API server: {e}")
        return
    try:
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        _server_started = True
        logger.info("API Server started at http://localhost:8000")
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")


def is_api_server_started():
    """Whether the debug API server has been started (e.g. by user clicking 开启调试模式)."""
    return _server_started

def stop_task(slot_id: str = "0"):
    with _slot_lock:
        ev = _slot_stop_events.get(slot_id)
        mgr = _slot_managers.get(slot_id)
    if ev:
        ev.set()
    if mgr:
        mgr.stop()
    logger.info(f"[slot={slot_id}] 收到停止信号。")


def _get_stop_event(slot_id: str) -> threading.Event:
    with _slot_lock:
        if slot_id not in _slot_stop_events:
            _slot_stop_events[slot_id] = threading.Event()
        return _slot_stop_events[slot_id]


def _set_manager(slot_id: str, manager):
    with _slot_lock:
        _slot_managers[slot_id] = manager


def _clear_manager(slot_id: str):
    with _slot_lock:
        _slot_managers.pop(slot_id, None)
        ev = _slot_stop_events.get(slot_id)
        if ev:
            ev.clear()

def log_comment_result(video_info, status, comment_text, source="Template", toast_message="", comment_log_path=None):
    path = comment_log_path or "comment_log.csv"
    file_exists = os.path.isfile(path)
    try:
        with open(path, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Time', 'BV', 'Title', 'Author', 'Status', 'Comment', 'Source', 'Toast'])
            
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                video_info.get('bv', ''),
                video_info.get('title', ''),
                video_info.get('author', ''),
                status,
                comment_text,
                source,
                toast_message
            ])
    except Exception as e:
        logger.error(f"Failed to write to log file: {e}")

def _check_and_fix_runasadmin(executable_path):
    if sys.platform != "win32":
        return
    try:
        import winreg
        reg_path = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
        norm_path = os.path.normpath(executable_path)
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
        except OSError:
            return
        try:
            value, _ = winreg.QueryValueEx(key, norm_path)
        except FileNotFoundError:
            winreg.CloseKey(key)
            return
        if "RUNASADMIN" not in value.upper():
            winreg.CloseKey(key)
            return
        parts = [p.strip() for p in value.split() if p.strip().upper() not in ("~", "RUNASADMIN")]
        if parts:
            new_value = " ".join(parts)
            winreg.SetValueEx(key, norm_path, 0, winreg.REG_SZ, new_value)
            logger.warning(f"已从兼容性设置中移除 RUNASADMIN 标志（保留其他标志: {new_value}）")
        else:
            try:
                winreg.DeleteValue(key, norm_path)
            except OSError:
                winreg.SetValueEx(key, norm_path, 0, winreg.REG_SZ, "")
            logger.warning("已移除浏览器的「以管理员身份运行」兼容性设置，否则 Playwright 无法启动该浏览器")
        winreg.CloseKey(key)
    except Exception as e:
        logger.warning(f"检查/修复 RUNASADMIN 兼容性标志时出错: {e}，如果浏览器启动失败，请手动取消 chrome.exe 属性中的「以管理员身份运行」")


def get_browser_launch_args(config, force_headed=False):
    headless = config.get("behavior", {}).get("headless", False)
    if force_headed:
        headless = False
        
    browser_config = config.get("browser", {})
    executable_path = browser_config.get("path", "")
    debug_port = browser_config.get("port", 0)
    
    launch_args = {
        "headless": headless,
        "args": [
            "--disable-infobars",
            "--window-size=1280,720",
            "--disable-blink-features=AutomationControlled",
            "--mute-audio",
            "--disable-gpu",
            "--disable-dev-shm-usage"
        ]
    }
    
    if executable_path:
        executable_path = os.path.normpath(executable_path)

    if executable_path and os.path.exists(executable_path):
        _check_and_fix_runasadmin(executable_path)
        launch_args["executable_path"] = executable_path
        launch_args["ignore_default_args"] = ["--no-sandbox"]
        
        logger.info(f"将使用指定路径拉起浏览器: {executable_path}")
        
        if headless:
             logger.info("使用外部浏览器，尝试以无头模式运行...")
    elif getattr(sys, 'frozen', False):
        logger.error("在打包环境中运行，必须在配置中指定浏览器路径！")
        return None
        
    if debug_port > 0:
        launch_args["args"].append(f"--remote-debugging-port={debug_port}")
    
    return launch_args

def main(video_callback=None, status_callback=None, workdir=None, slot_id="0", mode: str = "comment"):
    workdir = workdir or get_workdir(slot_id)
    ensure_slot_dir(slot_id)
    stop_ev = _get_stop_event(slot_id)
    _slot_token = slot_id_ctx.set(slot_id)
    try:
        _run_main(video_callback, status_callback, workdir, slot_id, stop_ev, mode=mode)
    finally:
        slot_id_ctx.reset(_slot_token)


def _run_main(video_callback, status_callback, workdir, slot_id, stop_ev, mode: str = "comment"):
    stop_ev.clear()
    config_path = get_config_path(slot_id)
    cookie_path = get_cookie_path(slot_id)
    comment_log_path = get_comment_log_path(slot_id)
    history_path = os.path.join(workdir, "history.json")

    logger.info(f"[主流程] 开始执行 - slot_id={slot_id}, mode={mode}")

    try:
        config = ConfigValidator.load_config(config_path)
        logger.info(f"[主流程] 配置加载成功")
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        return

    launch_args = get_browser_launch_args(config)
    logger.info(f"[主流程] 浏览器启动参数: {launch_args is not None}")
    if not launch_args:
        logger.error(f"[主流程] 浏览器启动参数为空，退出")
        return

    try:
        logger.info(f"[主流程] 启动 Playwright")
        # Python 3.13 兼容性：确保在正确的事件循环策略下运行
        import asyncio
        import sys
        if sys.platform == 'win32' and sys.version_info >= (3, 13):
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                logger.info(f"[主流程] 已设置 WindowsSelectorEventLoopPolicy")
            except Exception as e:
                logger.warning(f"[主流程] 设置事件循环策略失败: {e}")

        try:
            logger.info(f"[主流程] 调用 sync_playwright()")
            pw = sync_playwright().start()
            logger.info(f"[主流程] Playwright 已启动 - pw={pw}")
        except Exception as e:
            logger.error(f"[主流程] Playwright 启动失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return

        try:
            logger.info(f"[主流程] Playwright 上下文已创建 - p={pw}")
            browser = None
            context = None
            try:
                logger.info(f"[主流程] 启动浏览器 - launch_args={launch_args}")
                browser = pw.chromium.launch(**launch_args)
                logger.info(f"[主流程] 浏览器启动成功 - browser={browser}")
            except Exception as e:
                logger.error(f"启动浏览器失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return

            try:
                logger.info(f"[主流程] 创建浏览器上下文")
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1280, 'height': 720}
                )
                context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                logger.info(f"[主流程] 开始登录检查")
                auth = AuthManager(context, cookie_path, qrcode_path=get_qrcode_path(slot_id))
                if not auth.login():
                    logger.error("登录失败。正在退出。")
                    return
                logger.info(f"[主流程] 登录检查完成")

                search_page = context.new_page()
                comment_page = context.new_page()

                # Register page for debugging
                global_context.page = comment_page

                search_mgr = SearchManager(search_page)
                comment_mgr = CommentManager(comment_page)
                history_mgr = HistoryManager(file_path=history_path)
                captcha_tracker = CaptchaTracker()
                captcha_notifier = CaptchaNotifier()
                notification_mgr = get_notification_manager()
                # 更新通知管理器配置（初始化百度机器人等）
                notification_mgr.update_config(config)
                ai_manager = AIManager(config)

                # 根据模式决定本次任务是否启用 AI 评论 / AI 筛选
                mode = mode or "comment"
                if mode == "ai":
                    # 进入 AI 增强模式：只要有 provider 即视为可以用 AI 评论；
                    # 是否启用筛选仍由 ai.filter 配置决定
                    has_provider = ai_manager.provider is not None
                    ai_comment_enabled = has_provider
                    ai_filter_enabled = ai_manager.is_filter_enabled()
                else:
                    # 普通评论模式：完全不使用 AI（既不筛选，也不生成评论）
                    has_provider = False
                    ai_comment_enabled = False
                    ai_filter_enabled = False

                # #endregion
                # #endregion

                # 验证码冷却相关配置
                captcha_config = config.get("captcha", {})
                captcha_max_count = captcha_config.get("max_count", 3)
                captcha_quiet_minutes = captcha_config.get("quiet_minutes", 5)
                captcha_warmup_base = captcha_config.get("warmup_minutes", 30)
                cd_warmup_hours = captcha_config.get("cd_warmup_hours", 3)  # CD限制后养号时长（小时）

                # 动态延迟倍率（验证码触发后会增大）
                delay_multiplier = 1.0

                # CD 限制标志（触发后直接终止任务）
                cd_limit_triggered = False

                search_config = config.get("search", {})
                keywords = search_config.get("keywords", [])
                target_count = search_config.get("max_videos_per_keyword", 10)

                if not keywords:
                    logger.warning("配置中未找到搜索关键词，任务终止")
                    return

                # 发送任务开始通知
                notification_mgr.notify_task_started(
                    slot_id=slot_id,
                    task_type="评论任务",
                    target_count=target_count
                )

                total_success = 0
                captcha_terminated = False
                warmup_mgr = None  # lazy-loaded for captcha cooldown and interval warmup

                for keyword in keywords:
                    if stop_ev.is_set() or captcha_terminated or cd_limit_triggered: break
                    if total_success >= target_count: break

                    # 检查浏览器连接
                    if not is_browser_connected(browser):
                        logger.warning("浏览器连接已断开，终止任务")
                        return

                    logger.info(f"正在处理关键词: {keyword}")
                    is_first_page = True

                    while total_success < target_count and not stop_ev.is_set() and not captcha_terminated and not cd_limit_triggered:
                        # 检查浏览器连接
                        if not is_browser_connected(browser):
                            logger.warning("浏览器连接已断开，终止任务")
                            return

                        strategy_config = config.get("search", {}).get("strategy", {})
                        selection_mode = strategy_config.get("selection", "order")
                        strict_match = strategy_config.get("strict_title_match", False)
                        filter_config = config.get("search", {}).get("filter", {})
                
                        if is_first_page:
                            # 检查停止信号
                            if stop_ev.is_set():
                                logger.info("收到停止信号，终止任务")
                                break

                            videos = search_mgr.search_videos(
                                keyword,
                                max_count=1000,
                                order=filter_config.get("sort", "totalrank"),
                                duration=filter_config.get("duration", 0),
                                time_range=filter_config.get("time_range"),
                                stop_event=stop_ev
                            )
                            is_first_page = False
                        else:
                            videos = search_mgr.get_current_page_videos(max_count=1000)

                        if not videos: break

                        candidate_videos = []
                        skip_history = config.get("account", {}).get("skip_history", True)
                        for v in videos:
                            if skip_history and history_mgr.has(v['bv']): continue
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
                                    except Exception: continue
                            candidate_videos.append(v)

                        if candidate_videos:
                            if selection_mode == "random": random.shuffle(candidate_videos)
                            for video_info in candidate_videos:
                                # 检查停止信号
                                if stop_ev.is_set():
                                    logger.info("收到停止信号，终止任务")
                                    break

                                if total_success >= target_count or captcha_terminated or cd_limit_triggered:
                                    break

                                # 检查浏览器连接
                                if not is_browser_connected(browser):
                                    logger.warning("浏览器连接已断开，终止任务")
                                    return

                                # 检查重试上限
                                if not check_retry_limit(slot_id, "comment"):
                                    logger.error("评论操作失败次数过多，终止任务")
                                    notification_mgr.send_notification(
                                        title=f"实例 {slot_id} 连续失败",
                                        message=f"评论操作连续失败 {MAX_CONSECUTIVE_FAILURES} 次，任务已停止",
                                        notification_type="error",
                                        slot_id=slot_id,
                                        show_system=True,
                                    )
                                    return

                                if video_callback: video_callback(video_info)
                                if status_callback: status_callback(video_info['bv'], "处理中...")

                                # Fetch extended context for AI：按「智能筛选」内开关 use_comments / use_related 拉取；获取量优先用 comment 配置，否则用 filter
                                ai_cfg = config.get("ai", {})
                                filter_cfg = ai_cfg.get("filter", {})
                                comment_cfg = ai_cfg.get("comment", {})
                                max_comments = comment_cfg.get("max_comments") or filter_cfg.get("max_comments", 10)
                                max_related = comment_cfg.get("max_related") or filter_cfg.get("max_related", 5)
                                if (ai_filter_enabled or ai_comment_enabled) and \
                                        (filter_cfg.get("use_comments") or filter_cfg.get("use_related")):
                                    # 检查停止信号
                                    if stop_ev.is_set():
                                        logger.info("收到停止信号，终止任务")
                                        break

                                    from core.video_detail import fetch_top_comments, fetch_related_titles, truncate_comments
                                    need_comments = filter_cfg.get("use_comments")
                                    need_related = filter_cfg.get("use_related")
                                    if need_comments:
                                        raw_comments = fetch_top_comments(
                                            comment_page, video_info['url'],
                                            max_count=max_comments,
                                            stop_event=stop_ev
                                        )
                                        video_info["top_comments"] = truncate_comments(raw_comments)
                                    if need_related:
                                        related = fetch_related_titles(
                                            comment_page,
                                            max_count=max_related,
                                        )
                                        video_info["related_titles"] = "\n".join(related) if related else "(无)"

                                if ai_filter_enabled:
                                    # 检查停止信号
                                    if stop_ev.is_set():
                                        logger.info("收到停止信号，终止任务")
                                        break

                                    keep, reason = ai_manager.check_video_relevance(video_info)
                                    if not keep:
                                        logger.info(f"[AI筛选] 跳过视频: {video_info['title']} | 原因: {reason}")
                                        if status_callback: status_callback(video_info['bv'], f"AI跳过: {reason}")
                                        continue

                                comment_source = "Template"
                                text = None
                                if ai_comment_enabled:
                                    # 检查停止信号
                                    if stop_ev.is_set():
                                        logger.info("收到停止信号，终止任务")
                                        break

                                    text = ai_manager.generate_comment(video_info)
                                    if text:
                                        comment_source = "AI"
                                    else:
                                        logger.warning("AI 评论生成失败，降级使用模板")
                                if not text:
                                    comment_texts = config.get("comment", {}).get("texts", [])
                                    if comment_texts:
                                        text = random.choice(comment_texts)
                                    else:
                                        logger.error("配置中未找到评论文本，跳过评论")
                                        continue
                                image_path = None
                                if ai_comment_enabled:
                                    ai_comment_cfg = config.get("ai", {}).get("comment", {})
                                    ai_imgs = ai_comment_cfg.get("images")
                                    if isinstance(ai_imgs, str) and ai_imgs.strip():
                                        ai_imgs = [ai_imgs.strip()]
                                    elif not isinstance(ai_imgs, list):
                                        ai_imgs = []
                                    if ai_comment_cfg.get("enable_image", False) and ai_imgs and len(ai_imgs) > 0:
                                        image_path = random.choice(ai_imgs)
                                else:
                                    comment_imgs = config.get("comment", {}).get("images")
                                    if isinstance(comment_imgs, str) and comment_imgs.strip():
                                        comment_imgs = [comment_imgs.strip()]
                                    elif not isinstance(comment_imgs, list):
                                        comment_imgs = []
                                    if config.get("comment", {}).get("enable_image", False) and comment_imgs and len(comment_imgs) > 0:
                                        image_path = random.choice(comment_imgs)
                                if image_path and workdir and not os.path.isabs(image_path):
                                    image_path = os.path.join(workdir, image_path)

                                # 检查停止信号
                                if stop_ev.is_set():
                                    logger.info("收到停止信号，终止任务")
                                    break

                                result, toast_message = comment_mgr.post_comment(video_info['url'], text, image_path, stop_event=stop_ev)

                                # ===== 验证码冷却流程 =====
                                if result == "captcha":
                                    # 发送验证码提醒（立即通知）
                                    notification_mgr.notify_captcha_alert(
                                        slot_id=slot_id,
                                        source="comment",
                                        detail=video_info.get("bv") or video_info.get("url", "")
                                    )
                                    log_comment_result(video_info, "验证码拦截", text, comment_source, toast_message, comment_log_path=comment_log_path)
                                    if status_callback: status_callback(video_info['bv'], "验证码拦截", comment_content=text, comment_type=comment_source)

                                    # 1. 记录并获取今日累计次数
                                    captcha_count = captcha_tracker.record()

                                    # 发送验证码冷却通知
                                    notification_mgr.notify_captcha(slot_id, captcha_count, captcha_tracker.get_cooldown_minutes(captcha_warmup_base))

                                    # 2. 检查是否超过上限
                                    if captcha_count >= captcha_max_count:
                                        captcha_notifier.notify_terminated(captcha_count, captcha_max_count)
                                        notification_mgr.notify_terminated(slot_id, f"今日验证码触发已达上限（{captcha_count}/{captcha_max_count}）")
                                        captcha_terminated = True
                                        break

                                    # 3. 计算冷却时长
                                    cooldown_minutes = captcha_tracker.get_cooldown_minutes(captcha_warmup_base)

                                    # 4. 发送通知
                                    captcha_notifier.notify(captcha_count, cooldown_minutes, captcha_quiet_minutes)

                                    # 5. 静默等待（使用可中断等待）
                                    logger.info(f"[风控冷却] 开始静默等待 {captcha_quiet_minutes} 分钟...")
                                    if status_callback: status_callback(video_info['bv'], f"静默等待{captcha_quiet_minutes}分钟", comment_content=text, comment_type=comment_source)
                                    if interruptible_wait(stop_ev, captcha_quiet_minutes * 60):
                                        logger.info("静默等待期间收到停止信号，终止任务。")
                                        break

                                    # 6. 进入养号模式
                                    logger.info(f"[风控冷却] 静默结束，进入养号模式 {cooldown_minutes} 分钟...")
                                    if status_callback: status_callback(video_info['bv'], f"养号冷却{cooldown_minutes}分钟", comment_content=text, comment_type=comment_source)
                                    try:
                                        if warmup_mgr is None:
                                            # 传入 comment_page 复用现有页面，避免弹出新窗口
                                            warmup_mgr = WarmupManager(context, config, captcha_notifier, reuse_page=comment_page)
                                        _set_manager(slot_id, warmup_mgr)
                                        warmup_mgr.run(duration_override=cooldown_minutes)
                                    except Exception as e:
                                        logger.error(f"冷却养号过程出错: {e}")
                                    finally:
                                        _clear_manager(slot_id)

                                    # 7. 增大后续评论间隔
                                    delay_multiplier *= 1.5
                                    logger.info(f"[风控冷却] 冷却完成，评论间隔倍率已调整为 {delay_multiplier:.1f}x")

                                    # 跳过当前视频，继续下一个
                                    continue

                                # ===== CD限制冷却流程 =====
                                if result == "cd_limit":
                                    cd_start_time = datetime.now()
                                    logger.error(f"[风控CD] 检测到CD限制: {cd_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                                    log_comment_result(video_info, "CD限制", text, comment_source, toast_message, comment_log_path=comment_log_path)
                                    if status_callback: status_callback(video_info['bv'], "CD限制", comment_content=text, comment_type=comment_source)

                                    # 发送通知
                                    notification_mgr.notify_cd_limit(slot_id, cd_warmup_hours)

                                    # 设置 CD 限制标志，养号结束后直接终止任务
                                    cd_limit_triggered = True

                                    # 进入养号模式（使用配置的时长）
                                    logger.warning(f"[风控CD] 触发 CD 限制，进入 {cd_warmup_hours} 小时养号模式...")
                                    logger.warning(f"[风控CD] 养号结束后将自动停止任务，不再继续评论")
                                    if status_callback: status_callback(video_info['bv'], f"CD限制-养号{cd_warmup_hours}小时", comment_content=text, comment_type=comment_source)

                                    try:
                                        if warmup_mgr is None:
                                            # 传入 comment_page 复用现有页面，避免弹出新窗口
                                            warmup_mgr = WarmupManager(context, config, captcha_notifier, reuse_page=comment_page)
                                        _set_manager(slot_id, warmup_mgr)
                                        warmup_mgr.run(duration_override=cd_warmup_hours * 60)
                                    except Exception as e:
                                        logger.error(f"CD养号过程出错: {e}")
                                    finally:
                                        _clear_manager(slot_id)

                                    logger.info(f"[风控CD] {cd_warmup_hours} 小时养号完成，任务即将停止")

                                    # 跳出循环，终止任务
                                    break

                                # ===== 正常评论结果处理 =====
                                status = "成功" if result == "success" else "失败"
                                log_comment_result(video_info, status, text, comment_source, toast_message, comment_log_path=comment_log_path)
                                if status_callback: status_callback(video_info['bv'], status, comment_content=text, comment_type=comment_source)

                                if result == "success":
                                    history_mgr.add(video_info['bv'])
                                    total_success += 1
                                    # 成功时重置失败计数
                                    notification_mgr.reset_failure_count(slot_id)
                                    reset_retry_count(slot_id, "comment")

                                    # 发送评论成功通知（百度机器人）
                                    notification_mgr.notify_comment_success(
                                        slot_id=slot_id,
                                        video_title=video_info.get('title', '未知视频'),
                                        comment_text=text
                                    )
                                else:
                                    # 失败时记录（连续3次失败会自动发送通知）
                                    notification_mgr.notify_failure(slot_id, toast_message or "评论失败")

                                    # 发送单次评论失败通知（百度机器人）
                                    notification_mgr.notify_comment_failed(
                                        slot_id=slot_id,
                                        video_title=video_info.get('title', '未知视频'),
                                        reason=toast_message or "评论失败"
                                    )

                                base_min = config.get("behavior", {}).get("min_delay", 5)
                                base_max = config.get("behavior", {}).get("max_delay", 15)
                                delay = random.uniform(base_min * delay_multiplier, base_max * delay_multiplier)

                                # 读取大间隔自动养号配置
                                auto_warmup_config = config.get("warmup", {}).get("auto_warmup_on_large_interval", {})
                                auto_warmup_enabled = auto_warmup_config.get("enabled", True)  # 默认开启
                                auto_warmup_threshold = auto_warmup_config.get("threshold_seconds", 180)  # 默认 180 秒

                                if auto_warmup_enabled and delay >= auto_warmup_threshold:
                                    logger.info(f"评论间隔 {delay:.1f} 秒 ≥ {auto_warmup_threshold} 秒，进入养号模式填充间隔")
                                    if status_callback: status_callback(video_info['bv'], "养号填充间隔", comment_content=text, comment_type=comment_source)
                                    try:
                                        if warmup_mgr is None:
                                            # 传入 comment_page 复用现有页面，避免弹出新窗口
                                            warmup_mgr = WarmupManager(context, config, captcha_notifier, reuse_page=comment_page)
                                        _set_manager(slot_id, warmup_mgr)
                                        warmup_mgr.run(duration_override=delay / 60)
                                    except Exception as e:
                                        logger.error(f"间隔养号出错: {e}")
                                    finally:
                                        _clear_manager(slot_id)
                                    # 养号结束后恢复正常状态
                                    logger.info("养号填充完成，继续评论任务")
                                    if status_callback:
                                        status_callback(video_info['bv'], "评论成功", comment_content=text, comment_type=comment_source)
                                    if stop_ev.is_set():
                                        logger.info("养号期间收到停止信号，终止任务。")
                                        break
                                else:
                                    logger.info(f"评论间隔延迟: 等待 {delay:.1f} 秒后继续下一个视频...{' (间隔已因风控增大)' if delay_multiplier > 1.0 else ''}")
                                    if interruptible_wait(stop_ev, delay):
                                        logger.info("延迟期间收到停止信号，终止任务。")
                                        break

                        if total_success >= target_count or captcha_terminated or cd_limit_triggered or not search_mgr.go_to_next_page(): break

                    if cd_limit_triggered:
                        logger.warning(f"任务因触发 CD 限制而终止。本次成功评论: {total_success}/{target_count}")
                    elif captcha_terminated:
                        logger.info(f"任务因验证码次数达上限而终止。本次成功评论: {total_success}/{target_count}")
                    else:
                        logger.info(f"所有任务已完成。本次成功评论: {total_success}/{target_count}")

                    # 发送任务完成通知
                    notification_mgr.notify_task_completed(
                        slot_id=slot_id,
                        task_type="评论任务",
                        success_count=total_success,
                        total_count=target_count
                    )

            finally:
                # 确保资源清理
                try:
                    if context:
                        context.close()
                except Exception as e:
                    logger.debug(f"关闭 context 时出错: {e}")
                try:
                    if browser:
                        browser.close()
                except Exception as e:
                    logger.debug(f"关闭浏览器时出错: {e}")
        finally:
            # 确保 Playwright 停止
            try:
                pw.stop()
                logger.info(f"[主流程] Playwright 已停止")
            except Exception as e:
                logger.debug(f"停止 Playwright 时出错: {e}")

    except PlaywrightError as e:
        error_str = str(e)
        if "Browser closed" in error_str or "Target closed" in error_str or "Connection closed" in error_str:
            logger.warning(f"浏览器已关闭，任务终止: {error_str}")
        else:
            logger.error(f"Playwright 错误: {e}")
            import traceback
            traceback.print_exc()
    except Exception as e:
        logger.error(f"任务执行出错: {e}")
        import traceback
        traceback.print_exc()

def run_warmup(status_callback=None, workdir=None, slot_id="0"):
    workdir = workdir or get_workdir(slot_id)
    ensure_slot_dir(slot_id)
    stop_ev = _get_stop_event(slot_id)
    _slot_token = slot_id_ctx.set(slot_id)
    try:
        _run_warmup_impl(status_callback, workdir, slot_id, stop_ev)
    finally:
        slot_id_ctx.reset(_slot_token)


def _run_warmup_impl(status_callback, workdir, slot_id, stop_ev):
    stop_ev.clear()
    config_path = get_config_path(slot_id)
    cookie_path = get_cookie_path(slot_id)

    try:
        config = ConfigValidator.load_config(config_path)
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        return

    launch_args = get_browser_launch_args(config, force_headed=True)
    if not launch_args: return

    logger.info("养号模式强制使用有头浏览器（已静音）")

    try:
        # 手动启动 Playwright
        try:
            pw = sync_playwright().start()
            logger.info(f"[养号] Playwright 已启动")
        except Exception as e:
            logger.error(f"[养号] Playwright 启动失败: {e}")
            return

        try:
            browser = None
            context = None
            try:
                browser = pw.chromium.launch(**launch_args)
            except Exception as e:
                logger.error(f"启动浏览器失败: {e}")
                return

            try:
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1280, 'height': 720}
                )
                context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                auth = AuthManager(context, cookie_path, qrcode_path=get_qrcode_path(slot_id))
                if not auth.login():
                    logger.error("登录失败。正在退出。")
                    return

                warmup_mgr = WarmupManager(context, config, CaptchaNotifier())
                _set_manager(slot_id, warmup_mgr)
                try:
                    warmup_mgr.run(status_callback=status_callback)
                finally:
                    _clear_manager(slot_id)

            finally:
                # 确保资源清理
                try:
                    if context:
                        context.close()
                except Exception as e:
                    logger.debug(f"关闭 context 时出错: {e}")
                try:
                    if browser:
                        browser.close()
                except Exception as e:
                    logger.debug(f"关闭浏览器时出错: {e}")
        finally:
            # 确保 Playwright 停止
            try:
                pw.stop()
                logger.info(f"[养号] Playwright 已停止")
            except Exception as e:
                logger.debug(f"停止 Playwright 时出错: {e}")

    except PlaywrightError as e:
        error_str = str(e)
        if "Browser closed" in error_str or "Target closed" in error_str or "Connection closed" in error_str:
            logger.warning(f"浏览器已关闭，养号任务终止: {error_str}")
        else:
            logger.error(f"Playwright 错误: {e}")
            import traceback
            traceback.print_exc()
    except Exception as e:
        logger.error(f"养号任务执行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
