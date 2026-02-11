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

    COMMENT = {
        "container": "#commentapp, bili-comments",
        "bili_comments": "bili-comments",
        "comment_box": "bili-comment-box",
        "rich_textarea": "bili-comment-rich-textarea",
        "editor": ".brt-editor",
        "pictures_upload": "bili-comment-pictures-upload",
        "image_btn_icon": "BDC/image_line/3",
        "send_btn_selector": "#pub > button",
        "footer": "#footer",
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
    def get_bili_comments():
        return BilibiliSelectors.COMMENT["bili_comments"]

    @staticmethod
    def get_comment_box():
        return BilibiliSelectors.COMMENT["comment_box"]

    @staticmethod
    def get_rich_textarea():
        return BilibiliSelectors.COMMENT["rich_textarea"]

    @staticmethod
    def get_editor():
        return BilibiliSelectors.COMMENT["editor"]

    @staticmethod
    def get_pictures_upload():
        return BilibiliSelectors.COMMENT["pictures_upload"]

    @staticmethod
    def get_send_btn_selector():
        return BilibiliSelectors.COMMENT["send_btn_selector"]

    @staticmethod
    def get_footer():
        return BilibiliSelectors.COMMENT["footer"]
