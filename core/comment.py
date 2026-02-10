from playwright.sync_api import Page
from utils.logger import get_logger
import time
import os

logger = get_logger()

class CommentManager:
    def __init__(self, page: Page):
        self.page = page

    def post_comment(self, url: str, text: str, image_path: str = None) -> bool:
        """
        Post a comment to the video.
        """
        logger.info(f"Navigating to video: {url}")
        try:
            self.page.goto(url, wait_until="domcontentloaded")
            
            # Scroll to comment section
            try:
                # Scroll down significantly to trigger lazy loading of comments
                # Bilibili comments are often far down
                logger.info("Scrolling to find comment section...")
                self.page.evaluate("window.scrollTo(0, 2000)")
                time.sleep(1)
                self.page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(2) # Wait for lazy load
                
                # Wait for comment box
                # Updated selectors for 2024/2025
                # .reply-box-textarea: New standard
                # textarea.reply-input: Old fallback
                # div[contenteditable="true"]: Generic rich text editor
                # .bili-rich-text-input: Another variation
                selectors = ".reply-box-textarea, textarea.reply-input, div.bili-rich-text-input, div[contenteditable='true']"
                
                try:
                    self.page.wait_for_selector(selectors, timeout=10000)
                except:
                    # Try scrolling more if not found
                    self.page.evaluate("window.scrollBy(0, 1000)")
                    time.sleep(2)
                    self.page.wait_for_selector(selectors, timeout=10000)
                
                # Locate input
                comment_box = self.page.locator(selectors).first
                comment_box.scroll_into_view_if_needed()
            except:
                logger.error("Could not find comment box. Video might be restricted or loading failed.")
                return False

            # Click input to activate
            comment_box.click()
            time.sleep(1)

            # Handle Image Upload
            if image_path and os.path.exists(image_path):
                logger.info(f"Attempting to upload image: {image_path}")
                try:
                    upload_success = False
                    
                    # Strategy A: Direct Input Injection (If input exists in DOM)
                    file_input = self.page.locator("input[type='file']").first
                    if file_input.count() > 0:
                        logger.debug("Strategy A: Found existing file input. Injecting file...")
                        file_input.set_input_files(image_path)
                        upload_success = True
                    
                    # Strategy B: Click Icon + File Chooser (If input is hidden/dynamic)
                    if not upload_success:
                        logger.debug("Strategy B: Clicking image icon to trigger upload...")
                        # Selectors for the image upload icon
                        # .reply-box-image-icon: Common class
                        # .editor-tool-item.image: Another variation
                        # svg within tool bar
                        # Updated based on user feedback: button with bili-icon inside
                        # The button has class "tool-btn" and contains "bili-icon[icon*='image']"
                        icon_selectors = [
                            ".reply-box-image-icon", 
                            ".editor-tool-item.image", 
                            ".reply-toolbar .image-upload",
                            "button.tool-btn:has(bili-icon[icon*='image'])", # New selector
                            "button.tool-btn:has(bili-icon)" # Fallback broader
                        ]
                        
                        target_icon = None
                        for selector in icon_selectors:
                            if self.page.locator(selector).count() > 0:
                                target_icon = self.page.locator(selector).first
                                logger.info(f"Found image upload icon using selector: {selector}")
                                break
                        
                        if target_icon:
                            try:
                                with self.page.expect_file_chooser(timeout=5000) as fc_info:
                                    target_icon.click()
                                
                                file_chooser = fc_info.value
                                file_chooser.set_files(image_path)
                                upload_success = True
                            except Exception as e:
                                logger.warning(f"Failed during file chooser interaction: {e}")
                        else:
                            logger.warning("Could not find image upload icon.")

                    # Wait for upload completion
                    if upload_success:
                        logger.info("Image file selected. Waiting for upload preview...")
                        # Wait for preview image to appear
                        # .reply-image-preview, .image-preview-item
                        try:
                            self.page.wait_for_selector(".reply-image-preview, .image-preview-item, .preview-img", timeout=10000)
                            logger.info("Image upload confirmed (preview visible).")
                            time.sleep(2) # Extra buffer for server processing
                        except:
                            logger.warning("Timeout waiting for image preview. Upload might have failed or preview selector changed.")
                    
                except Exception as e:
                    logger.warning(f"Image upload failed: {e}")
            elif image_path:
                logger.error(f"Image file not found: {image_path}")

            # Type text
            logger.info(f"Typing comment: {text}")
            comment_box.fill(text)
            time.sleep(1)
            
            # Click Send
            logger.info("Locating send button...")
            try:
                # Try to find the button relative to the comment box container
                # Usually they are siblings or in a common container
                
                # Strategy 1: Standard selectors
                send_selectors = ".reply-box-send-btn, .send-text, div.reply-box-send-btn"
                
                # Strategy 2: Text based (fallback)
                # "发布" is the standard text for the button
                
                send_btn = None
                
                if self.page.locator(send_selectors).count() > 0:
                     send_btn = self.page.locator(send_selectors).first
                else:
                     logger.info("Standard selectors failed, trying text locator '发布'...")
                     send_btn = self.page.get_by_text("发布", exact=True).first
                
                if not send_btn:
                     # Try finding button inside the same container as the input
                     # This is a bit heuristic
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
            
            # Verify success
            # 1. Input cleared?
            # 2. Success message?
            # 3. Captcha popup?
            
            time.sleep(3)
            
            # Check for captcha
            if self.page.locator(".geetest_window, .bili-mini-mask").count() > 0:
                logger.error("CAPTCHA detected! Please solve it manually if running in headful mode.")
                # If headless, we are stuck.
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
