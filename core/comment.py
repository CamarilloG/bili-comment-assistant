from playwright.sync_api import Page
from utils.logger import get_logger
from core.selectors import BilibiliSelectors
from utils.retry import retry
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import time
import os

logger = get_logger()

class CommentManager:
    def __init__(self, page: Page):
        self.page = page

    @retry(max_attempts=2, delay=3.0, exceptions=(PlaywrightTimeoutError,))
    def post_comment(self, url: str, text: str, image_path: str = None) -> bool:
        """
        Post a comment to the video.
        """
        logger.info(f"Navigating to video: {url}")
        try:
            self.page.goto(url, wait_until="domcontentloaded")
            
            # Scroll to comment section
            try:
                logger.info("Scrolling to find comment section...")
                
                # 1. Try to find the container first as anchor
                container_selector = BilibiliSelectors.get_comment_container()
                try:
                    # Try to find container without scrolling first (sometimes already visible)
                    if self.page.locator(container_selector).count() > 0:
                        self.page.locator(container_selector).first.scroll_into_view_if_needed()
                    else:
                        # Scroll down to trigger lazy load
                        # Try to scroll to bottom first as comments are usually at bottom
                        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        self.page.wait_for_timeout(1000)
                        
                        # Wait for container
                        self.page.wait_for_selector(container_selector, timeout=5000)
                        self.page.locator(container_selector).first.scroll_into_view_if_needed()
                except Exception:
                    logger.debug("Comment container not found immediately, trying step-by-step scroll.")
                
                # 2. Loop to find input box
                selectors = BilibiliSelectors.get_comment_input()
                found_input = False
                
                for i in range(10): # Try scrolling 10 times
                    try:
                        if self.page.locator(selectors).count() > 0 and self.page.locator(selectors).first.is_visible():
                            found_input = True
                            break
                        
                        # Scroll down a bit
                        self.page.evaluate("window.scrollBy(0, 500)")
                        self.page.wait_for_timeout(500)
                    except:
                        pass
                
                if not found_input:
                     # Final attempt: wait explicitly
                     try:
                         self.page.wait_for_selector(selectors, timeout=5000)
                     except:
                         pass

                # Locate input
                comment_box = self.page.locator(selectors).first
                comment_box.scroll_into_view_if_needed()
                
                # Ensure it's ready
                self.page.wait_for_selector(selectors, state="visible", timeout=5000)
                
            except Exception as e:
                logger.error(f"Could not find comment box: {e}. Video might be restricted or loading failed.")
                return False

            comment_box.click()
            self.page.wait_for_timeout(500)

            # Handle Image Upload
            if image_path and os.path.exists(image_path):
                logger.info(f"Attempting to upload image: {image_path}")
                try:
                    upload_success = False
                    
                    file_input = self.page.locator(BilibiliSelectors.COMMENT["file_input"]).first
                    if file_input.count() > 0:
                        logger.debug("Strategy A: Found existing file input. Injecting file...")
                        file_input.set_input_files(image_path)
                        upload_success = True
                    
                    if not upload_success:
                        logger.debug("Strategy B: Clicking image icon to trigger upload...")
                        icon_selectors = BilibiliSelectors.get_image_upload_icons()
                        
                        target_icon = None
                        for selector in icon_selectors:
                            if self.page.locator(selector).count() > 0:
                                target_icon = self.page.locator(selector).first
                                logger.info(f"Found image upload icon using selector: {selector}")
                                break
                        
                        if target_icon:
                            try:
                                # Sometimes clicking doesn't trigger chooser immediately or browser blocks it
                                # We try to setup handler first
                                with self.page.expect_file_chooser(timeout=5000) as fc_info:
                                    # Ensure icon is clickable
                                    target_icon.scroll_into_view_if_needed()
                                    target_icon.click(force=True)
                                
                                file_chooser = fc_info.value
                                file_chooser.set_files(image_path)
                                upload_success = True
                            except Exception as e:
                                logger.warning(f"Failed during file chooser interaction: {e}. Maybe permissions issue or chooser didn't open.")
                        else:
                            logger.warning("Could not find image upload icon.")

                    # Wait for upload completion
                    if upload_success:
                        logger.info("Image file selected. Waiting for upload preview...")
                        try:
                            self.page.wait_for_selector(BilibiliSelectors.COMMENT["image_preview"], timeout=10000)
                            logger.info("Image upload confirmed (preview visible).")
                            self.page.wait_for_timeout(1000)
                        except Exception:
                            logger.warning("Timeout waiting for image preview. Upload might have failed or preview selector changed.")
                    
                except Exception as e:
                    logger.warning(f"Image upload failed: {e}")
            elif image_path:
                logger.error(f"Image file not found: {image_path}")

            logger.info(f"Typing comment: {text}")
            comment_box.fill(text)
            self.page.wait_for_timeout(500)
            
            # Click Send
            logger.info("Locating send button...")
            try:
                # BilibiliSelectors.get_comment_send_button() returns a list now
                send_selectors = BilibiliSelectors.get_comment_send_button()
                send_btn = None
                
                # Iterate through list of selectors
                for selector in send_selectors:
                    if self.page.locator(selector).count() > 0:
                        send_btn = self.page.locator(selector).first
                        logger.info(f"Found send button using selector: {selector}")
                        break
                
                if not send_btn:
                     logger.info("Standard selectors failed, trying text locator '发布'...")
                     send_btn = self.page.get_by_text("发布", exact=True).first
                
                if not send_btn:
                     logger.warning("Could not locate send button directly. Trying broader search.")
                     send_btn = self.page.locator("button").filter(has_text="发布").first

                if send_btn:
                    # Check if disabled
                    # Sometimes it's a div, so is_enabled() might always be true unless it checks class
                    if not send_btn.is_enabled():
                        logger.warning("Send button is disabled (maybe empty content or not logged in?).")
                    
                    logger.info("Clicking send button...")
                    send_btn.click(force=True) # Force click in case of overlays
                    logger.info("Clicked send button.")
                else:
                    logger.error("Could not find ANY send button.")
                    return False
            
            except Exception as e:
                logger.error(f"Error clicking send button: {e}")
                return False
            
            self.page.wait_for_timeout(2000)
            
            if self.page.locator(BilibiliSelectors.COMMENT["captcha"]).count() > 0:
                logger.error("CAPTCHA detected! Please solve it manually if running in headful mode.")
                return False
                
            # Validation logic
            # Handle both input/textarea and contenteditable div
            try:
                tag_name = comment_box.evaluate("el => el.tagName.toLowerCase()")
                current_value = ""
                
                if tag_name in ['input', 'textarea']:
                    current_value = comment_box.input_value()
                else:
                    # For contenteditable divs
                    current_value = comment_box.inner_text().strip()
                    
                if current_value == "":
                    logger.info("Comment posted successfully (input cleared).")
                    return True
                else:
                    logger.warning(f"Comment might not have been sent (input not cleared). Remaining text: {current_value[:20]}...")
                    return False
            except Exception as val_err:
                logger.warning(f"Validation failed but comment might have been sent: {val_err}")
                return True

        except Exception as e:
            logger.error(f"Error posting comment: {e}")
            return False
