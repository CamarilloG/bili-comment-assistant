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
        logger.info(f"正在导航至视频: {url}")
        try:
            self.page.goto(url, wait_until="domcontentloaded")
            
            # Scroll to comment section
            try:
                logger.info("正在滚动查找评论区...")
                
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
                    logger.debug("未立即找到评论区容器，尝试逐步滚动。")
                
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
                logger.error(f"无法找到评论框: {e}. 视频可能受限或加载失败。")
                return False

            comment_box.click()
            self.page.wait_for_timeout(500)

            # Handle Image Upload
            if image_path and os.path.exists(image_path):
                logger.info(f"尝试上传图片: {image_path}")
                try:
                    upload_success = False
                    
                    file_input = self.page.locator(BilibiliSelectors.COMMENT["file_input"]).first
                    if file_input.count() > 0:
                        logger.debug("策略 A: 发现现有文件输入框。注入文件...")
                        file_input.set_input_files(image_path)
                        upload_success = True
                    
                    if not upload_success:
                        logger.debug("策略 B: 点击图片图标触发上传...")
                        icon_selectors = BilibiliSelectors.get_image_upload_icons()
                        
                        target_icon = None
                        for selector in icon_selectors:
                            if self.page.locator(selector).count() > 0:
                                target_icon = self.page.locator(selector).first
                                logger.info(f"使用选择器找到图片上传图标: {selector}")
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
                                logger.warning(f"文件选择器交互失败: {e}. 可能是权限问题或选择器未打开。")
                        else:
                            logger.warning("未找到图片上传图标。")

                    # Wait for upload completion
                    if upload_success:
                        logger.info("已选择图片文件。等待上传预览...")
                        try:
                            self.page.wait_for_selector(BilibiliSelectors.COMMENT["image_preview"], timeout=10000)
                            logger.info("图片上传确认 (预览可见)。")
                            self.page.wait_for_timeout(1000)
                        except Exception:
                            logger.warning("等待图片预览超时。上传可能失败或预览选择器已更改。")
                    
                except Exception as e:
                    logger.warning(f"图片上传失败: {e}")
            elif image_path:
                logger.error(f"未找到图片文件: {image_path}")

            logger.info(f"输入评论: {text}")
            comment_box.fill(text)
            self.page.wait_for_timeout(500)
            
            # Click Send
            logger.info("正在定位发送按钮...")
            try:
                # BilibiliSelectors.get_comment_send_button() returns a list now
                send_selectors = BilibiliSelectors.get_comment_send_button()
                send_btn = None
                
                # Iterate through list of selectors
                for selector in send_selectors:
                    if self.page.locator(selector).count() > 0:
                        send_btn = self.page.locator(selector).first
                        logger.info(f"使用选择器找到发送按钮: {selector}")
                        break
                
                if not send_btn:
                     logger.info("标准选择器失败，尝试文本定位 '发布'...")
                     send_btn = self.page.get_by_text("发布", exact=True).first
                
                if not send_btn:
                     logger.warning("无法直接定位发送按钮。尝试更广泛的搜索。")
                     send_btn = self.page.locator("button").filter(has_text="发布").first

                if send_btn:
                    # Check if disabled
                    # Sometimes it's a div, so is_enabled() might always be true unless it checks class
                    if not send_btn.is_enabled():
                        logger.warning("发送按钮已禁用 (可能内容为空或未登录?)")
                    
                    logger.info("正在点击发送按钮...")
                    send_btn.click(force=True) # Force click in case of overlays
                    logger.info("已点击发送按钮。")
                else:
                    logger.error("无法找到任何发送按钮。")
                    return False
            
            except Exception as e:
                logger.error(f"点击发送按钮出错: {e}")
                return False
            
            self.page.wait_for_timeout(2000)
            
            if self.page.locator(BilibiliSelectors.COMMENT["captcha"]).count() > 0:
                logger.error("检测到验证码！如果是真实模式请手动解决。")
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
                    logger.info("评论发布成功 (输入框已清空)。")
                    return True
                else:
                    logger.warning(f"评论可能未发送 (输入框未清空)。剩余文本: {current_value[:20]}...")
                    return False
            except Exception as val_err:
                logger.warning(f"验证失败，但评论可能已发送: {val_err}")
                return True

        except Exception as e:
            logger.error(f"发布评论出错: {e}")
            return False
