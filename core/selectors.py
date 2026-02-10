class BilibiliSelectors:
    # Login
    LOGIN = {
        "avatar": ".header-avatar-wrap, .bili-avatar, .header-entry-avatar, .v-popover-wrap",
        "login_btn": ".header-login-entry",
        "qr_img": ".qrcode-img img"
    }

    # Search
    SEARCH = {
        "video_card": ".video-list .bili-video-card, .bili-video-card, .video-item, .video-list-item, .bili-video-card__wrap",
        "link": "a[href*='video/BV']",
        "title": ".bili-video-card__info--tit, h3.t, .title",
        "author": ".bili-video-card__info--author, .up-name, .author",
        "date": ".bili-video-card__info--date, .time",
        "stats": ".bili-video-card__stats--item, .so-icon-watch-num, .so-icon-time",
        "next_page": ".vui_pagenation--btns button:has-text('下一页'), .vui_pagenation--btn-side:has-text('下一页'), .pages .next"
    }

    # Filters
    FILTER = {
        "1day": ".search-condition-row button:has-text('最近一天')",
        "1week": ".search-condition-row button:has-text('最近一周')",
        "6months": ".search-condition-row button:has-text('最近半年')",
        "all_dates": ".search-condition-row button:has-text('全部日期')",
        "date_picker_trigger": ".search-date-picker__trigger",
        "date_picker_panel": ".search-date-picker"
    }

    @staticmethod
    def get_search_video_cards():
        return BilibiliSelectors.SEARCH["video_card"]

    @staticmethod
    def get_search_video_link():
        return BilibiliSelectors.SEARCH["link"]

    # Comment
    COMMENT = {
        "container": "#comment, .comment-container, .comment-m-v, .comment-app",
        "input": ".reply-box-textarea, textarea.reply-input, div.bili-rich-text-input, div[contenteditable='true']",
        "send_btn": [
            ".reply-box-send-btn", 
            ".send-text", 
            "div.reply-box-send-btn",
            "button.reply-box-send-btn"
        ],
        "image_icon": [
            ".reply-box-image-icon", 
            ".editor-tool-item.image", 
            ".reply-toolbar .image-upload",
            "button.tool-btn:has(bili-icon[icon*='image'])",
            "button.tool-btn:has(bili-icon)"
        ],
        "image_preview": ".reply-image-preview, .image-preview-item, .preview-img",
        "file_input": "input[type='file']",
        "captcha": ".geetest_window, .bili-mini-mask"
    }

    @staticmethod
    def get_login_avatar():
        return BilibiliSelectors.LOGIN["avatar"]

    @staticmethod
    def get_login_button():
        return BilibiliSelectors.LOGIN["login_btn"]

    @staticmethod
    def get_comment_container():
        return BilibiliSelectors.COMMENT["container"]

    @staticmethod
    def get_comment_input():
        return BilibiliSelectors.COMMENT["input"]
        
    @staticmethod
    def get_comment_send_button():
        return BilibiliSelectors.COMMENT["send_btn"]

    @staticmethod
    def get_image_upload_icons():
        return BilibiliSelectors.COMMENT["image_icon"]
