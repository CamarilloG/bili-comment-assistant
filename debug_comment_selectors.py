from playwright.sync_api import sync_playwright
import json
import os
import time

def test_comment_flow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        if os.path.exists("cookies.json"):
            with open("cookies.json", 'r', encoding='utf-8') as f:
                context.add_cookies(json.load(f))
        
        page = context.new_page()
        page.goto("https://www.bilibili.com/video/BV16ZsTeCEZn", wait_until="domcontentloaded")
        
        print("Waiting for page to load...")
        time.sleep(5)
        
        print("\n=== Step 1: Scroll to find comment box ===")
        for i in range(12):
            result = page.evaluate("""() => {
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
            }""")
            if result:
                print(f"  FOUND comment box after {i+1} scrolls!")
                break
            page.evaluate("window.scrollBy(0, 500)")
            time.sleep(0.8)
        else:
            print("  FAILED to find comment box!")
            input("Press Enter to close...")
            browser.close()
            return

        print("\n=== Step 2: Click editor ===")
        click_result = page.evaluate("""() => {
            const biliComments = document.querySelector('bili-comments');
            if (!biliComments || !biliComments.shadowRoot) return 'no bili-comments shadow';
            const boxes = biliComments.shadowRoot.querySelectorAll('bili-comment-box');
            for (const box of boxes) {
                if (!box.shadowRoot) continue;
                const textarea = box.shadowRoot.querySelector('bili-comment-rich-textarea');
                if (!textarea || !textarea.shadowRoot) continue;
                const editor = textarea.shadowRoot.querySelector('.brt-editor');
                if (editor) {
                    editor.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    editor.click();
                    editor.focus();
                    return 'ok';
                }
            }
            return 'editor not found';
        }""")
        print(f"  Click result: {click_result}")
        time.sleep(1)

        print("\n=== Step 3: Input text ===")
        input_result = page.evaluate("""(text) => {
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
        }""", "测试评论文本 - 请勿发送")
        print(f"  Input result: {input_result}")
        time.sleep(1)

        print("\n=== Step 4: Check footer visibility ===")
        footer_info = page.evaluate("""() => {
            const biliComments = document.querySelector('bili-comments');
            if (!biliComments || !biliComments.shadowRoot) return 'no shadow';
            const boxes = biliComments.shadowRoot.querySelectorAll('bili-comment-box');
            for (const box of boxes) {
                if (!box.shadowRoot) continue;
                const footer = box.shadowRoot.querySelector('#footer');
                if (!footer) continue;
                return {
                    className: footer.className,
                    display: getComputedStyle(footer).display,
                    visibility: getComputedStyle(footer).visibility,
                    buttons: [...footer.querySelectorAll('button')].map(b => ({
                        class: b.className,
                        text: b.innerText.trim(),
                        display: getComputedStyle(b).display
                    }))
                };
            }
            return 'no footer';
        }""")
        print(f"  Footer info: {json.dumps(footer_info, indent=2, ensure_ascii=False)}")

        print("\n=== Step 5: Check image button ===")
        img_btn_info = page.evaluate("""() => {
            const biliComments = document.querySelector('bili-comments');
            if (!biliComments || !biliComments.shadowRoot) return 'no shadow';
            const boxes = biliComments.shadowRoot.querySelectorAll('bili-comment-box');
            for (const box of boxes) {
                if (!box.shadowRoot) continue;
                const buttons = box.shadowRoot.querySelectorAll('button.tool-btn');
                const result = [];
                for (const btn of buttons) {
                    const icon = btn.querySelector('bili-icon');
                    result.push({
                        class: btn.className,
                        iconAttr: icon ? icon.getAttribute('icon') : null,
                        isImageBtn: icon && icon.getAttribute('icon') && icon.getAttribute('icon').includes('image')
                    });
                }
                return result;
            }
            return 'no box';
        }""")
        print(f"  Image button info: {json.dumps(img_btn_info, indent=2, ensure_ascii=False)}")

        print("\n=== Step 6: Check send button ===")
        send_info = page.evaluate("""() => {
            const biliComments = document.querySelector('bili-comments');
            if (!biliComments || !biliComments.shadowRoot) return 'no shadow';
            const boxes = biliComments.shadowRoot.querySelectorAll('bili-comment-box');
            for (const box of boxes) {
                if (!box.shadowRoot) continue;
                const pubDiv = box.shadowRoot.querySelector('#pub');
                if (!pubDiv) continue;
                const btn = pubDiv.querySelector('button');
                if (btn) {
                    return {
                        text: btn.innerText.trim(),
                        class: btn.className,
                        disabled: btn.disabled
                    };
                }
            }
            return 'no send btn';
        }""")
        print(f"  Send button info: {json.dumps(send_info, indent=2, ensure_ascii=False)}")

        print("\n=== Step 7: Check pictures upload component ===")
        pu_info = page.evaluate("""() => {
            const biliComments = document.querySelector('bili-comments');
            if (!biliComments || !biliComments.shadowRoot) return 'no shadow';
            const boxes = biliComments.shadowRoot.querySelectorAll('bili-comment-box');
            for (const box of boxes) {
                if (!box.shadowRoot) continue;
                const pu = box.shadowRoot.querySelector('bili-comment-pictures-upload');
                if (!pu) continue;
                return {
                    found: true,
                    hasShadow: !!pu.shadowRoot,
                    shadowHTML: pu.shadowRoot ? pu.shadowRoot.innerHTML.substring(0, 2000) : '',
                    hasFileInput: pu.shadowRoot ? !!pu.shadowRoot.querySelector('input[type="file"]') : false
                };
            }
            return { found: false };
        }""")
        print(f"  Pictures upload info: {json.dumps(pu_info, indent=2, ensure_ascii=False)}")

        print("\n=== All tests complete! ===")
        print("NOTE: Text was entered but NOT sent. Close browser manually to verify.")
        input("Press Enter to close browser...")
        browser.close()

if __name__ == "__main__":
    test_comment_flow()
