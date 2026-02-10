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
            logger.info(f"Loading cookies from {self.cookie_file}")
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                    self.context.add_cookies(cookies)
                
                if self._check_login_status():
                    logger.info("Login successful using cookies.")
                    return True
                else:
                    logger.warning("Cookies expired or invalid.")
            except Exception as e:
                logger.error(f"Error loading cookies: {e}")
        
        return self._qr_login()

    def _check_login_status(self) -> bool:
        """
        Check if current session is logged in by visiting a user page.
        """
        page = self.context.new_page()
        try:
            logger.debug("Checking login status...")
            page.goto("https://www.bilibili.com/", wait_until="domcontentloaded")
            
            # Wait for header to load
            try:
                # Use a more generic selector for header
                page.wait_for_selector(".bili-header, .header-entry-avatar", timeout=10000)
            except Exception:
                logger.warning("Timeout waiting for header elements.")
            
            if page.locator(BilibiliSelectors.get_login_avatar()).count() > 0:
                logger.debug("Avatar found. User is logged in.")
                return True
                
            if page.locator(BilibiliSelectors.get_login_button()).count() > 0:
                logger.debug("Login entry found. User is NOT logged in.")
                return False
                
            # Fallback
            return False
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return False
        finally:
            page.close()

    def _qr_login(self):
        """
        Perform QR code login.
        """
        logger.info("Starting QR code login...")
        page = self.context.new_page()
        try:
            page.goto("https://passport.bilibili.com/login", wait_until="domcontentloaded")
            logger.info("Please scan the QR code to login in the opened browser window.")
            
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
                    logger.info("SESSDATA cookie found. Login likely successful.")
                    break
                    
                # Check if URL changed significantly
                if "passport.bilibili.com/login" not in page.url:
                    logger.info("URL changed, assuming login successful.")
                    break
                
                time.sleep(2)
            
            # After loop, verify strictly
            if self._check_login_status():
                logger.info("QR Login successful.")
                self._save_cookies()
                return True
            else:
                logger.error("Login failed or timed out.")
                return False
        finally:
            page.close()

    def _save_cookies(self):
        cookies = self.context.cookies()
        with open(self.cookie_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2)
        logger.info(f"Cookies saved to {self.cookie_file}")
