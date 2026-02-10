import json
import os
import time
from playwright.sync_api import BrowserContext, Page
from utils.logger import get_logger
from core.selectors import BilibiliSelectors

logger = get_logger()

class AuthManager:
    def __init__(self, context: BrowserContext, cookie_file: str = "cookies.json"):
        self.context = context
        self.cookie_file = cookie_file

    def login(self):
        """
        Perform login flow.
        1. Try to load cookies.
        2. Check if logged in.
        3. If not, perform QR login.
        """
        if os.path.exists(self.cookie_file):
            logger.info(f"正在从 {self.cookie_file} 加载 Cookies")
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                    self.context.add_cookies(cookies)
                
                if self._check_login_status():
                    logger.info("使用 Cookies 登录成功。")
                    return True
                else:
                    logger.warning("Cookies 已过期或无效。")
            except Exception as e:
                logger.error(f"加载 Cookies 出错: {e}")
        
        return self._qr_login()

    def _check_login_status(self) -> bool:
        """
        Check if current session is logged in by visiting a user page.
        """
        page = self.context.new_page()
        try:
            logger.debug("正在检查登录状态...")
            page.goto("https://www.bilibili.com/", wait_until="domcontentloaded")
            
            # Wait for header to load
            try:
                # Use a more generic selector for header
                page.wait_for_selector(".bili-header, .header-entry-avatar", timeout=10000)
            except Exception:
                logger.warning("等待头部元素超时。")
            
            if page.locator(BilibiliSelectors.get_login_avatar()).count() > 0:
                logger.debug("找到头像。用户已登录。")
                return True
                
            if page.locator(BilibiliSelectors.get_login_button()).count() > 0:
                logger.debug("找到登录入口。用户未登录。")
                return False
                
            # Fallback
            return False
        except Exception as e:
            logger.error(f"检查登录状态出错: {e}")
            return False
        finally:
            page.close()

    def _qr_login(self):
        """
        Perform QR code login.
        """
        logger.info("开始扫码登录...")
        page = self.context.new_page()
        try:
            page.goto("https://passport.bilibili.com/login", wait_until="domcontentloaded")
            logger.info("请在打开的浏览器窗口中扫描二维码登录。")
            
            # Loop to check login status
            start_time = time.time()
            while time.time() - start_time < 120: # 2 minutes timeout
                # Active polling for login status
                # 1. Check if we are still on login page (URL check)
                # 2. Check for success cookies or elements in the page
                
                # Check cookies first (fastest)
                cookies = self.context.cookies()
                # Bilibili login usually sets SESSDATA
                sessdata = next((c for c in cookies if c['name'] == 'SESSDATA'), None)
                if sessdata:
                    logger.info("找到 SESSDATA Cookie。登录可能已成功。")
                    break
                    
                # Check if URL changed significantly
                if "passport.bilibili.com/login" not in page.url:
                    logger.info("URL 已更改，假设登录成功。")
                    break
                
                time.sleep(2)
            
            # After loop, verify strictly
            if self._check_login_status():
                logger.info("扫码登录成功。")
                self._save_cookies()
                return True
            else:
                logger.error("登录失败或超时。")
                return False
        finally:
            page.close()

    def _save_cookies(self):
        cookies = self.context.cookies()
        with open(self.cookie_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2)
        logger.info(f"Cookies 已保存至 {self.cookie_file}")
