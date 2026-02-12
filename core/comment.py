from playwright.sync_api import Page
from utils.logger import get_logger
from core.selectors import BilibiliSelectors
from utils.retry import retry
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import time
import os

logger = get_logger()

JS_SCROLL_TO_COMMENT_BOX = """() => {
    const biliComments = document.querySelector('bili-comments');
    if (!biliComments || !biliComments.shadowRoot) return null;
    const boxes = biliComments.shadowRoot.querySelectorAll('bili-comment-box');
    for (const box of boxes) {
        if (!box.shadowRoot) continue;
        const footer = box.shadowRoot.querySelector('#footer');
        if (!footer) continue;
        biliComments.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return true;
    }
    return null;
}"""

JS_ACTIVATE_EDITOR = """() => {
    const biliComments = document.querySelector('bili-comments');
    if (!biliComments || !biliComments.shadowRoot) return 'no bili-comments shadow';
    const boxes = biliComments.shadowRoot.querySelectorAll('bili-comment-box');
    for (const box of boxes) {
        if (!box.shadowRoot) continue;
        const textarea = box.shadowRoot.querySelector('bili-comment-rich-textarea');
        if (!textarea || !textarea.shadowRoot) continue;
        const editor = textarea.shadowRoot.querySelector('.brt-editor');
        if (editor) {
            const footer = box.shadowRoot.querySelector('#footer');
            if (footer) {
                footer.classList.remove('hidden');
                footer.style.display = '';
            }
            editor.scrollIntoView({ behavior: 'smooth', block: 'center' });
            editor.click();
            editor.focus();
            return 'ok';
        }
    }
    return 'editor not found';
}"""

JS_INPUT_TEXT = """(text) => {
    const biliComments = document.querySelector('bili-comments');
    if (!biliComments || !biliComments.shadowRoot) return 'no bili-comments shadow';
    const boxes = biliComments.shadowRoot.querySelectorAll('bili-comment-box');
    for (const box of boxes) {
        if (!box.shadowRoot) continue;
        const textarea = box.shadowRoot.querySelector('bili-comment-rich-textarea');
        if (!textarea || !textarea.shadowRoot) continue;
        const editor = textarea.shadowRoot.querySelector('.brt-editor');
        if (editor) {
            editor.focus();
            editor.innerText = text;
            editor.dispatchEvent(new Event('input', { bubbles: true }));
            editor.dispatchEvent(new Event('change', { bubbles: true }));
            return 'ok';
        }
    }
    return 'editor not found';
}"""

JS_HOVER_BODY_AND_PREPARE = """() => {
    const biliComments = document.querySelector('bili-comments');
    if (!biliComments || !biliComments.shadowRoot) return 'no bili-comments shadow';
    const boxes = biliComments.shadowRoot.querySelectorAll('bili-comment-box');
    for (const box of boxes) {
        if (!box.shadowRoot) continue;
        const body = box.shadowRoot.querySelector('#body');
        if (body) {
            body.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
            body.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
        }
        const footer = box.shadowRoot.querySelector('#footer');
        if (footer) {
            footer.classList.remove('hidden');
            footer.style.display = '';
        }
        return 'ok';
    }
    return 'no comment box';
}"""

JS_CLICK_IMAGE_BTN = """() => {
    const biliComments = document.querySelector('bili-comments');
    if (!biliComments || !biliComments.shadowRoot) return 'no bili-comments shadow';
    const boxes = biliComments.shadowRoot.querySelectorAll('bili-comment-box');
    for (const box of boxes) {
        if (!box.shadowRoot) continue;
        const buttons = box.shadowRoot.querySelectorAll('button.tool-btn');
        for (const btn of buttons) {
            const icon = btn.querySelector('bili-icon');
            if (icon && icon.getAttribute('icon') && icon.getAttribute('icon').includes('image')) {
                btn.scrollIntoView({ block: 'center' });
                btn.click();
                return 'ok';
            }
        }
    }
    return 'image btn not found';
}"""

JS_GET_FILE_INPUT_HANDLE = """() => {
    const biliComments = document.querySelector('bili-comments');
    if (!biliComments || !biliComments.shadowRoot) return null;
    const boxes = biliComments.shadowRoot.querySelectorAll('bili-comment-box');
    for (const box of boxes) {
        if (!box.shadowRoot) continue;
        const pu = box.shadowRoot.querySelector('bili-comment-pictures-upload');
        if (pu && pu.shadowRoot) {
            const fi = pu.shadowRoot.querySelector('input[type="file"]');
            if (fi) return fi;
        }
        const fi2 = box.shadowRoot.querySelector('input[type="file"]');
        if (fi2) return fi2;
    }
    return null;
}"""

JS_CLICK_SEND = """() => {
    const biliComments = document.querySelector('bili-comments');
    if (!biliComments || !biliComments.shadowRoot) return 'no bili-comments shadow';
    const boxes = biliComments.shadowRoot.querySelectorAll('bili-comment-box');
    for (const box of boxes) {
        if (!box.shadowRoot) continue;
        const pubDiv = box.shadowRoot.querySelector('#pub');
        if (pubDiv) {
            const btn = pubDiv.querySelector('button');
            if (btn) {
                btn.scrollIntoView({ block: 'center' });
                btn.click();
                return 'ok';
            }
        }
        const allBtns = box.shadowRoot.querySelectorAll('button');
        for (const btn of allBtns) {
            if (btn.textContent.trim().includes('发布')) {
                btn.scrollIntoView({ block: 'center' });
                btn.click();
                return 'ok';
            }
        }
    }
    return 'send btn not found';
}"""

JS_GET_EDITOR_TEXT = """() => {
    const biliComments = document.querySelector('bili-comments');
    if (!biliComments || !biliComments.shadowRoot) return null;
    const boxes = biliComments.shadowRoot.querySelectorAll('bili-comment-box');
    for (const box of boxes) {
        if (!box.shadowRoot) continue;
        const textarea = box.shadowRoot.querySelector('bili-comment-rich-textarea');
        if (!textarea || !textarea.shadowRoot) continue;
        const editor = textarea.shadowRoot.querySelector('.brt-editor');
        if (editor) return editor.innerText.trim();
    }
    return null;
}"""

JS_CHECK_UPLOAD_PREVIEW = """() => {
    const biliComments = document.querySelector('bili-comments');
    if (!biliComments || !biliComments.shadowRoot) return false;
    const boxes = biliComments.shadowRoot.querySelectorAll('bili-comment-box');
    for (const box of boxes) {
        if (!box.shadowRoot) continue;
        const pu = box.shadowRoot.querySelector('bili-comment-pictures-upload');
        if (pu && pu.shadowRoot) {
            const imgs = pu.shadowRoot.querySelectorAll('img, .preview, [class*="preview"], [class*="image"]');
            if (imgs.length > 0) return true;
        }
    }
    return false;
}"""


class CommentManager:
    def __init__(self, page: Page):
        self.page = page

    def _scroll_to_comments(self):
        logger.info("正在滚动查找评论区...")
        for i in range(12):
            result = self.page.evaluate(JS_SCROLL_TO_COMMENT_BOX)
            if result:
                self.page.wait_for_timeout(500)
                logger.debug("找到评论框组件并滚动到可见区域。")
                return True
            self.page.evaluate("window.scrollBy(0, 500)")
            self.page.wait_for_timeout(800)

        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.page.wait_for_timeout(2000)
        result = self.page.evaluate(JS_SCROLL_TO_COMMENT_BOX)
        if result:
            self.page.wait_for_timeout(500)
            logger.debug("滚动到底部后找到评论框。")
            return True

        logger.error("未找到评论框组件 (bili-comment-box)。")
        return False

    def _activate_editor(self):
        result = self.page.evaluate(JS_ACTIVATE_EDITOR)
        if result != 'ok':
            logger.error(f"激活编辑器失败: {result}")
            return False
        self.page.wait_for_timeout(500)
        logger.debug("评论编辑器已激活。")
        return True

    def _input_text(self, text: str):
        result = self.page.evaluate(JS_INPUT_TEXT, text)
        if result != 'ok':
            logger.error(f"输入文本失败: {result}")
            return False
        self.page.wait_for_timeout(300)
        logger.debug(f"已输入文本: {text[:30]}...")
        return True

    def _upload_image(self, image_path: str) -> bool:
        logger.info(f"尝试上传图片: {image_path}")

        self._activate_editor()
        self.page.wait_for_timeout(800)

        self.page.evaluate(JS_HOVER_BODY_AND_PREPARE)
        self.page.wait_for_timeout(500)

        for attempt in range(3):
            try:
                logger.debug(f"图片上传尝试 {attempt + 1}/3...")

                with self.page.expect_file_chooser(timeout=5000) as fc_info:
                    click_result = self.page.evaluate(JS_CLICK_IMAGE_BTN)
                    if click_result != 'ok':
                        logger.debug(f"尝试 {attempt + 1}: 点击图片按钮失败: {click_result}")
                        self.page.evaluate(JS_HOVER_BODY_AND_PREPARE)
                        self.page.wait_for_timeout(1000)
                        continue

                file_chooser = fc_info.value
                file_chooser.set_files(image_path)
                logger.info("已通过文件选择器上传图片。")
                self.page.wait_for_timeout(3000)
                return True
            except Exception as e:
                logger.debug(f"尝试 {attempt + 1} 失败: {e}")
                self.page.evaluate(JS_HOVER_BODY_AND_PREPARE)
                self.page.wait_for_timeout(1000)

        logger.warning("图片上传失败，将仅发送文本评论。")
        return False

    def _click_send(self):
        result = self.page.evaluate(JS_CLICK_SEND)
        if result != 'ok':
            logger.error(f"点击发送按钮失败: {result}")
            return False
        logger.info("已点击发送按钮。")
        return True

    def _check_captcha(self) -> bool:
        """检测页面上是否存在验证码弹窗

        Returns:
            True 表示检测到验证码，False 表示未检测到
        """
        try:
            captcha_selectors = BilibiliSelectors.COMMENT["captcha"]
            if self.page.locator(captcha_selectors).count() > 0:
                logger.error(
                    "[风控] 检测到极验验证码(geetest)！"
                    "B站风控系统已拦截当前操作，将放弃本次评论并进入冷却流程。"
                )
                return True
            # 额外检测 geetest_widget（验证码主容器）
            if self.page.locator(".geetest_widget").count() > 0:
                logger.error(
                    "[风控] 检测到极验验证码弹窗(geetest_widget)！"
                    "B站风控系统已拦截当前操作，将放弃本次评论并进入冷却流程。"
                )
                return True
        except Exception as e:
            logger.debug(f"验证码检测过程出现异常: {e}")
        return False

    def _verify_sent(self) -> str:
        """验证评论是否发送成功

        Returns:
            "success" - 评论发布成功
            "captcha" - 检测到验证码，触发风控
            "failed"  - 发送失败（非验证码原因）
        """
        self.page.wait_for_timeout(2000)

        if self._check_captcha():
            return "captcha"

        editor_text = self.page.evaluate(JS_GET_EDITOR_TEXT)
        if editor_text is not None and editor_text == "":
            logger.info("评论发布成功 (输入框已清空)。")
            return "success"
        elif editor_text is not None:
            logger.warning(f"评论可能未发送 (输入框未清空)。剩余文本: {editor_text[:20]}...")
            return "failed"
        else:
            logger.warning("无法验证发送状态，假定已发送。")
            return "success"

    @retry(max_attempts=2, delay=3.0, exceptions=(PlaywrightTimeoutError,))
    def post_comment(self, url: str, text: str, image_path: str = None) -> str:
        """发布评论到指定视频

        Returns:
            "success" - 评论发布成功
            "captcha" - 检测到验证码，触发风控
            "failed"  - 发送失败（非验证码原因）
        """
        logger.info(f"正在导航至视频: {url}")
        try:
            self.page.goto(url, wait_until="domcontentloaded")
            self.page.wait_for_timeout(2000)

            # 导航完成后立即检测验证码（风控可能在页面加载时就触发）
            if self._check_captcha():
                logger.warning("[风控] 页面加载后即检测到验证码，可能是导航阶段触发的风控拦截。")
                return "captcha"

            if not self._scroll_to_comments():
                return "failed"

            if not self._activate_editor():
                return "failed"

            if image_path and os.path.exists(image_path):
                self._upload_image(image_path)
            elif image_path:
                logger.error(f"未找到图片文件: {image_path}")

            logger.info(f"输入评论: {text}")
            if not self._input_text(text):
                return "failed"

            self.page.wait_for_timeout(500)

            logger.info("正在定位发送按钮...")
            self.page.evaluate(JS_HOVER_BODY_AND_PREPARE)
            self.page.wait_for_timeout(300)
            if not self._click_send():
                return "failed"

            return self._verify_sent()

        except Exception as e:
            logger.error(f"发布评论出错: {e}")
            # 检查异常是否由验证码/风控导致的页面异常引起
            if self._check_captcha():
                logger.warning("[风控] 评论过程异常且检测到验证码，判定为风控拦截。")
                return "captcha"
            return "failed"
