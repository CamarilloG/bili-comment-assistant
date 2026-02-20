from playwright.sync_api import Page
from utils.logger import get_logger
from core.selectors import BilibiliSelectors
from core.captcha_check import check_captcha_on_page
from utils.retry import retry
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import time
import os

logger = get_logger()

class CommentManager:
    def __init__(self, page: Page):
        self.page = page

    def _get_main_comment_box(self):
        """
        获取主评论框组件 (位于 bili-comments-header-renderer 内部)
        结构: bili-comments -> bili-comments-header-renderer -> bili-comment-box
        """
        # 使用 locator 链穿透 Shadow DOM
        # 1. bili-comments
        # 2. bili-comments-header-renderer
        # 3. bili-comment-box
        return (self.page
                .locator("bili-comments")
                .locator("bili-comments-header-renderer")
                .locator("bili-comment-box")
                .first)

    def _editor(self):
        """
        获取编辑器元素 (.brt-editor)
        路径: [Main Box] -> #comment-area -> #body -> #editor -> bili-comment-rich-textarea -> #input -> .brt-root -> .brt-editor
        """
        # 简化路径，直接从 main box 找
        return (self._get_main_comment_box()
                .locator("bili-comment-rich-textarea")
                .locator(".brt-editor")
                .first)

    def _send_button(self):
        """
        获取发送按钮
        路径: [Main Box] -> #comment-area -> #footer -> #pub -> button
        """
        # 优先查找 #pub 下的按钮 (根据提供的 HTML 实例，这是最准确的)
        btn = self._get_main_comment_box().locator("#pub button").first
        
        # 兜底：查找包含“发布”文本的按钮
        if btn.count() == 0:
            btn = self._get_main_comment_box().locator("button:has-text('发布')").first
            
        return btn

    def _scroll_to_comments(self) -> bool:
        logger.info("正在滚动查找评论区...")
        
        # 策略: 滚动到 bili-comments 组件
        anchors = ["bili-comments", "#commentapp", "#comment", ".comment-m"]
        
        found_anchor = False
        for anchor in anchors:
            if self.page.locator(anchor).count() > 0:
                try:
                    # 滚动到中心
                    self.page.evaluate(f"document.querySelector('{anchor}').scrollIntoView({{block: 'center', behavior: 'smooth'}})")
                    self.page.wait_for_timeout(1000)
                    found_anchor = True
                    break
                except:
                    pass
        
        if not found_anchor:
            # 兜底滚动到底部
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(1000)

        try:
            # 等待懒加载完成
            # 1. 等待 bili-comments 组件 attached
            self.page.locator("bili-comments").wait_for(state="attached", timeout=10000)
            
            # 2. 等待主评论框出现
            # 我们直接等待 bili-comments-header-renderer 里的 bili-comment-box
            self._get_main_comment_box().wait_for(state="attached", timeout=15000)
            
            logger.debug("评论区组件已加载。")
            
            # 再次滚动到评论框
            self._get_main_comment_box().scroll_into_view_if_needed()
            return True
        except Exception as e:
            logger.warning(f"查找评论区超时或失败: {e}")
            return False

    def _activate_editor(self) -> bool:
        try:
            box = self._get_main_comment_box()
            if box.count() == 0:
                return False
                
            box.scroll_into_view_if_needed()
            
            # 1. 模拟鼠标移动到评论框中心 (触发 hover 状态)
            # 根据 HTML，hover 会使 #editor 增加 active 类，并显示 footer
            bbox = box.bounding_box()
            if bbox:
                self.page.mouse.move(bbox["x"] + bbox["width"] / 2, bbox["y"] + bbox["height"] / 2)
                self.page.wait_for_timeout(500)
            
            # 2. 点击编辑器
            editor = self._editor()
            editor.wait_for(state="visible", timeout=5000)
            editor.click()
            editor.focus()
            
            self.page.wait_for_timeout(500)
            logger.debug("评论编辑器已激活。")
            return True
        except Exception as e:
            logger.error(f"激活编辑器失败: {e}")
            return False

    def _input_text(self, text: str) -> bool:
        try:
            editor = self._editor()
            editor.click()
            editor.focus()
            
            # 清除内容
            editor.press("Control+A")
            editor.press("Backspace")
            self.page.wait_for_timeout(200)

            # 模拟键盘输入
            self.page.keyboard.type(text, delay=100)
            self.page.wait_for_timeout(500)
            
            # 检查是否写入成功，如果失败尝试 JS 注入
            current_text = editor.inner_text()
            if not current_text.strip():
                logger.warning("键盘输入未生效，尝试 JS 赋值...")
                editor.evaluate(f"el => {{ el.innerText = '{text}'; }}")
            
            # 手动触发 React/Vue 事件
            editor.evaluate("""el => { 
                el.dispatchEvent(new Event('input', { bubbles: true })); 
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur', { bubbles: true }));
                el.dispatchEvent(new Event('focus', { bubbles: true }));
            }""")
            
            self.page.wait_for_timeout(500)
            return True
        except Exception as e:
            logger.error(f"输入文本失败: {e}")
            return False

    def _upload_image(self, image_path: str) -> bool:
        logger.info(f"尝试上传图片: {image_path}")
        if not self._activate_editor():
            return False

        try:
            # 定位图片上传按钮
            # 路径: [Main Box] -> #comment-area -> #footer -> button.tool-btn (containing bili-icon[icon*='image'])
            # 注意：HTML 中 class 是 " tool-btn "，locator('.tool-btn') 可以匹配
            # 也可以直接找 icon
            img_btn = (self._get_main_comment_box()
                       .locator("button.tool-btn")
                       .filter(has=self.page.locator("bili-icon[icon*='image']"))
                       .first)
            
            if img_btn.count() == 0:
                # 尝试更宽松的定位
                img_btn = (self._get_main_comment_box()
                           .locator("bili-icon[icon*='image']")
                           .locator("xpath=..") # 父级 button
                           .first)

            with self.page.expect_file_chooser(timeout=5000) as fc_info:
                img_btn.click()
            
            fc = fc_info.value
            fc.set_files(image_path)
            
            # 等待预览图片出现
            # bili-comment-pictures-upload -> template -> #content -> img/.preview
            preview = (self._get_main_comment_box()
                       .locator("bili-comment-pictures-upload")
                       .locator("img, .preview")
                       .first)
            
            # 给一点时间上传和渲染
            try:
                preview.wait_for(state="attached", timeout=15000)
                logger.info("图片已上传并显示预览。")
                return True
            except:
                logger.warning("图片上传后未检测到预览，可能失败。")
                return False
                
        except Exception as e:
            logger.warning(f"图片上传流程出错: {e}")
            return False

    def _click_send(self) -> bool:
        try:
            btn = self._send_button()
            
            # 检查按钮是否存在
            try:
                btn.wait_for(state="attached", timeout=5000)
                # 如果被遮挡（例如被 footer 边缘遮挡），尝试滚动
                btn.scroll_into_view_if_needed()
            except:
                logger.error("发送按钮未找到或未加载。")
                return False

            # 检查禁用状态
            if btn.is_disabled():
                logger.error("发送按钮处于禁用状态。")
                return False
            
            # 强制点击
            btn.click(force=True)
            logger.info("已点击发送按钮。")
            return True
        except Exception as e:
            logger.error(f"点击发送按钮失败: {e}")
            return False

    def _check_captcha(self) -> bool:
        try:
            if check_captcha_on_page(self.page):
                logger.error("[风控] 检测到验证码弹窗！")
                return True
            return False
        except Exception:
            return False

    def _verify_sent(self) -> str:
        # 1. 检查风控
        if self._check_captcha(): return "captcha"
        
        # 2. 优先尝试捕获 Toast 提示
        try:
            # Toast 通常在 .b-toast-container .b-toast
            toast = self.page.locator(".b-toast-container .b-toast").first
            # 等待 Toast 出现，超时时间 4秒
            toast.wait_for(state="visible", timeout=4000)
            text = toast.inner_text().strip()
            logger.info(f"捕获到发送提示: {text}")
            
            if "成功" in text:
                return "success"
            elif "验证码" in text or "频繁" in text or "禁言" in text:
                logger.warning(f"发送失败，提示: {text}")
                return "failed"
            else:
                logger.warning(f"未知的发送提示: {text}")
                # 继续走兜底逻辑
        except Exception:
            # Toast 未出现或超时，不抛出错误，继续走后续兜底逻辑
            logger.debug("未捕获到 Toast 提示，尝试检查输入框状态。")

        try:
            # 3. 兜底：等待输入框清空
            editor = self._editor()
            # 轮询检查文本是否为空
            for _ in range(10): # 5秒
                if not editor.inner_text().strip():
                    logger.info("评论发布成功 (输入框已清空)。")
                    return "success"
                self.page.wait_for_timeout(500)
                if self._check_captcha(): return "captcha"
            
            logger.warning("发送后输入框未清空，可能发送失败。")
            return "failed"
        except Exception as e:
            logger.warning(f"验证发送状态出错: {e}")
            return "failed"

    @retry(max_attempts=2, delay=3.0, exceptions=(PlaywrightTimeoutError,))
    def post_comment(self, url: str, text: str, image_path: str = None) -> str:
        logger.info(f"正在导航至视频: {url}")
        try:
            self.page.goto(url, wait_until="domcontentloaded")
            
            if self._check_captcha():
                return "captcha"

            if not self._scroll_to_comments():
                return "failed"

            if not self._activate_editor():
                return "failed"

            if image_path and os.path.exists(image_path):
                self._upload_image(image_path)

            logger.info(f"输入评论: {text}")
            if not self._input_text(text):
                return "failed"
            
            if not self._click_send():
                return "failed"

            return self._verify_sent()

        except Exception as e:
            logger.error(f"发布评论出错: {e}")
            return "failed"
