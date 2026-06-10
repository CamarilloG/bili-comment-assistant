"""DM Flow: independent task entry that orchestrates search -> scrape -> filter -> send DM.

This module is fully independent from main.py; it manages its own Playwright browser lifecycle.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
from datetime import datetime
from typing import Callable, Dict, List, Optional

from playwright.sync_api import sync_playwright

from core.auth import AuthManager
from core.search import SearchManager
from core.comment_scraper import CommentScraper
from core.user_filter import filter_users
from core.dm_sender import DmSender, DmHistory
from core.ai_manager import AIManager
from core.config import ConfigValidator
from core.slot import get_workdir, get_config_path, get_cookie_path, get_qrcode_path, ensure_slot_dir
from utils.logger import get_logger, slot_id_ctx

logger = get_logger()

_slot_stop_events: Dict[str, threading.Event] = {}
_slot_lock = threading.Lock()


def _get_stop_event(slot_id: str) -> threading.Event:
    with _slot_lock:
        if slot_id not in _slot_stop_events:
            _slot_stop_events[slot_id] = threading.Event()
        return _slot_stop_events[slot_id]


def stop_dm_task(slot_id: str = "0"):
    with _slot_lock:
        ev = _slot_stop_events.get(slot_id)
    if ev:
        ev.set()
    logger.info(f"[DM slot={slot_id}] 收到停止信号")


def _interruptible_wait(stop_event: threading.Event, seconds: float) -> bool:
    """Wait up to *seconds*; return True if interrupted."""
    elapsed = 0.0
    while elapsed < seconds:
        if stop_event.wait(min(1.0, seconds - elapsed)):
            return True
        elapsed += 1.0
    return False


def _get_browser_launch_args(config: dict):
    """Build Playwright launch args from config, same logic as main.py."""
    from main import get_browser_launch_args
    return get_browser_launch_args(config)


def run_dm(
    status_callback: Optional[Callable] = None,
    workdir: Optional[str] = None,
    slot_id: str = "0",
):
    """Public entry point for the DM task."""
    workdir = workdir or get_workdir(slot_id)
    ensure_slot_dir(slot_id)
    stop_ev = _get_stop_event(slot_id)
    token = slot_id_ctx.set(slot_id)
    try:
        _run_dm_impl(status_callback, workdir, slot_id, stop_ev)
    finally:
        slot_id_ctx.reset(token)


def _run_dm_impl(
    status_callback: Optional[Callable],
    workdir: str,
    slot_id: str,
    stop_ev: threading.Event,
):
    stop_ev.clear()
    config_path = get_config_path(slot_id)
    cookie_path = get_cookie_path(slot_id)

    logger.info(f"[DM] 开始执行 - slot_id={slot_id}")

    try:
        config = ConfigValidator.load_config(config_path)
    except Exception as e:
        logger.error(f"[DM] 配置加载失败: {e}")
        return

    dm_cfg = config.get("dm_flow", {})
    if not dm_cfg:
        logger.error("[DM] 配置中缺少 dm_flow 段，请在私信模式设置中配置")
        return

    search_cfg = dm_cfg.get("search", {})
    if not search_cfg.get("keywords", []):
        logger.error("[DM] No search keywords configured")
        return

    launch_args = _get_browser_launch_args(config)
    if not launch_args:
        logger.error("[DM] 浏览器启动参数为空，退出")
        return

    # Stats for frontend
    stats = {"total_scraped": 0, "filtered": 0, "sent": 0, "failed": 0, "limited": 0}

    def _notify(status: str):
        if status_callback:
            try:
                status_callback(status, dict(stats))
            except Exception:
                pass

    # ---------- Playwright lifecycle ----------
    import asyncio
    if sys.platform == "win32" and sys.version_info >= (3, 13):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass

    pw = None
    browser = None
    context = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(**launch_args)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        auth = AuthManager(context, cookie_path, qrcode_path=get_qrcode_path(slot_id))
        if not auth.login():
            logger.error("[DM] 登录失败，退出")
            return

        search_page = context.new_page()
        scrape_page = context.new_page()
        dm_page = context.new_page()

        search_mgr = SearchManager(search_page)
        scraper = CommentScraper(scrape_page)

        delay_range = dm_cfg.get("dm", {}).get("delay_range", [8, 20])
        sender = DmSender(dm_page, delay_range=tuple(delay_range[:2]))

        dm_history_path = os.path.join(workdir, "dm_history.json")
        history = DmHistory(dm_history_path)

        # AI manager (optional) — 强制启用 provider，不依赖主模式开关
        ai_manager = None
        filter_cfg = dm_cfg.get("filter", {})
        if filter_cfg.get("use_ai", False):
            try:
                patched_config = dict(config)
                ai_section = dict(patched_config.get("ai", {}))
                ai_section.setdefault("filter", {})["enabled"] = True
                ai_section["filter"].setdefault("criteria", filter_cfg.get("ai_prompt", "dm"))
                patched_config["ai"] = ai_section
                ai_manager = AIManager(patched_config)
                if ai_manager.provider is None:
                    logger.warning("[DM] AI provider 未初始化，请在「AI 设置」页面配置 API Key 和模型")
                    ai_manager = None
            except Exception as e:
                logger.warning(f"[DM] AI 管理器初始化失败: {e}")

        # ---------- Search ----------
        search_cfg = dm_cfg.get("search", {})
        keywords = search_cfg.get("keywords", [])
        max_videos = search_cfg.get("max_videos_per_keyword", 5)
        order = search_cfg.get("order", "pubdate")
        search_duration = search_cfg.get("duration", 0)
        search_time_range = search_cfg.get("time_range", None)
        search_strategy = search_cfg.get("strategy", "order")

        if not keywords:
            logger.error("[DM] 未配置搜索关键词")
            return

        max_per_run = dm_cfg.get("dm", {}).get("max_per_run", 30)
        skip_sent = dm_cfg.get("dm", {}).get("skip_already_sent", True)
        dm_template = dm_cfg.get("dm", {}).get("template", "")
        max_comments = dm_cfg.get("comment_scrape", {}).get("max_comments_per_video", 200)

        regex_patterns = filter_cfg.get("regex_patterns", [])
        use_ai = filter_cfg.get("use_ai", False)
        ai_prompt = filter_cfg.get("ai_prompt", "")

        _notify("running")

        for keyword in keywords:
            if stop_ev.is_set():
                break
            if stats["sent"] >= max_per_run:
                logger.info(f"[DM] 已达发送上限 {max_per_run}，停止")
                break

            logger.info(f"[DM] 搜索关键词: {keyword}")
            videos = search_mgr.search_videos(
                keyword, max_count=max_videos, order=order,
                duration=search_duration, time_range=search_time_range,
                stop_event=stop_ev,
            )
            if search_strategy == "random" and len(videos) > max_videos:
                import random
                videos = random.sample(videos, max_videos)
            logger.info(f"[DM] 找到 {len(videos)} 个视频")

            for video in videos:
                if stop_ev.is_set():
                    break
                if stats["sent"] >= max_per_run:
                    break

                url = video.get("url", "")
                title = video.get("title", "")
                if not url:
                    continue

                logger.info(f"[DM] 处理视频: {title}")

                # ---------- Scrape comments ----------
                comments = scraper.scrape_comments(url, max_count=max_comments, stop_event=stop_ev)
                stats["total_scraped"] += len(comments)
                _notify("scraping")

                if not comments:
                    logger.info(f"[DM] 视频 {title} 无评论可抓取")
                    continue

                # 持久化评论到本地文件
                try:
                    dump_dir = os.path.join(workdir, "dm_comments")
                    os.makedirs(dump_dir, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:40]
                    dump_path = os.path.join(dump_dir, f"{ts}_{safe_title}.json")
                    with open(dump_path, "w", encoding="utf-8") as f:
                        json.dump({"video_url": url, "title": title, "count": len(comments), "comments": comments}, f, ensure_ascii=False, indent=2)
                    logger.info(f"[DM] 评论已保存到 {dump_path}")
                except Exception as e:
                    logger.debug(f"[DM] 评论保存失败: {e}")

                if comments:
                    sample = comments[0]
                    logger.info(f"[DM] 评论样本: uid={sample.get('uid','')} uname={sample.get('uname','')} content={sample.get('content','')[:80]}")

                # ---------- Filter ----------
                candidates = filter_users(
                    comments,
                    regex_patterns=regex_patterns if regex_patterns else None,
                    use_ai=use_ai,
                    ai_criteria=ai_prompt,
                    ai_manager=ai_manager,
                )
                stats["filtered"] += len(candidates)
                _notify("filtering")

                # ---------- Send DMs ----------
                for user in candidates:
                    if stop_ev.is_set():
                        break
                    if stats["sent"] >= max_per_run:
                        break

                    uid = user.get("uid", "")
                    uname = user.get("uname", "")
                    if not uid:
                        continue

                    if skip_sent and history.is_sent(uid):
                        logger.debug(f"[DM] 跳过已发送: uid={uid} uname={uname}")
                        continue

                    content = dm_template.replace("{uname}", uname) if dm_template else ""
                    if not content:
                        logger.warning("[DM] 私信模板为空，跳过")
                        continue

                    logger.info(f"[DM] 发送私信给 uid={uid} uname={uname}")
                    result = sender.send_dm(uid, content, stop_event=stop_ev)

                    if result == "ok":
                        stats["sent"] += 1
                        history.record(uid, uname, "ok")
                    elif result == "limited":
                        stats["limited"] += 1
                        history.record(uid, uname, "limited")
                    elif result == "stopped":
                        break
                    else:
                        stats["failed"] += 1
                        history.record(uid, uname, "failed")

                    _notify("sending")
                    sender.wait_between_sends(stop_event=stop_ev)

        logger.info(
            f"[DM] 流程结束 - 抓取:{stats['total_scraped']} "
            f"筛选:{stats['filtered']} 发送:{stats['sent']} "
            f"受限:{stats['limited']} 失败:{stats['failed']}"
        )
        _notify("completed")

    except Exception as e:
        logger.error(f"[DM] 流程异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        _notify("error")
    finally:
        try:
            if context:
                context.close()
            if browser:
                browser.close()
            if pw:
                pw.stop()
        except Exception:
            pass
