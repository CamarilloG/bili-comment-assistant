# 点击视频卡片进入详情页的JavaScript代码

CLICK_VIDEO_CARD_JS = """
(videoId) => {
    // 根据视频ID查找对应的卡片
    const containerId = `waterfall_item_${videoId}`;
    const container = document.getElementById(containerId);
    
    if (!container) {
        console.error('[抖音点击] 未找到容器:', containerId);
        return { success: false, error: '未找到视频容器' };
    }
    
    // 查找卡片元素
    const card = container.querySelector('.search-result-card');
    if (!card) {
        console.error('[抖音点击] 未找到卡片');
        return { success: false, error: '未找到视频卡片' };
    }
    
    // 滚动到卡片位置
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    
    // 模拟点击 - 使用多种方式确保点击生效
    card.click();
    
    // 同时触发鼠标事件
    const mouseEvent = new MouseEvent('click', {
        view: window,
        bubbles: true,
        cancelable: true,
        clientX: card.getBoundingClientRect().left + card.offsetWidth / 2,
        clientY: card.getBoundingClientRect().top + card.offsetHeight / 2
    });
    card.dispatchEvent(mouseEvent);
    
    console.log('[抖音点击] 已点击视频卡片:', videoId);
    return { success: true, videoId: videoId };
}
"""

GET_VIDEO_DETAIL_INFO_JS = """
() => {
    // 在视频详情页提取信息
    const info = {
        url: window.location.href,
        title: '',
        author: '',
        likes: '',
        comments: '',
        shares: '',
        description: ''
    };
    
    try {
        // 提取标题 - 优先使用 h1 标签
        const h1 = document.querySelector('h1');
        if (h1 && h1.innerText.trim()) {
            info.title = h1.innerText.trim();
        } else {
            // 备用选择器
            const titleSelectors = [
                '[data-e2e="video-title"]',
                '[class*="title"]',
                '[class*="Title"]'
            ];
            for (const selector of titleSelectors) {
                const elem = document.querySelector(selector);
                if (elem && elem.innerText.trim()) {
                    info.title = elem.innerText.trim();
                    break;
                }
            }
        }
        
        // 提取作者 - 查找用户链接，排除导航链接
        const userLinks = document.querySelectorAll('a[href*="/user/"]');
        for (const link of userLinks) {
            const text = link.innerText.trim();
            // 排除导航链接（如"我的"）和空文本
            if (text && text !== '我的' && text.length < 50) {
                info.author = text;
                break;
            }
        }
        
        // 如果没找到，尝试其他选择器
        if (!info.author) {
            const authorSelectors = [
                '[data-e2e="video-author-name"]',
                '[data-e2e="user-name"]',
                '[class*="author-name"]',
                '[class*="user-name"]',
                '[class*="UserName"]'
            ];
            for (const selector of authorSelectors) {
                const elem = document.querySelector(selector);
                if (elem && elem.innerText.trim()) {
                    info.author = elem.innerText.trim();
                    break;
                }
            }
        }
        
        // 提取点赞数 - 查找包含数字的交互元素
        const likeSelectors = [
            '[data-e2e="like-count"]',
            '[class*="like-count"]',
            '[class*="LikeCount"]',
            'span[class*="like"]'
        ];
        for (const selector of likeSelectors) {
            const elem = document.querySelector(selector);
            if (elem && elem.innerText.trim() && /\d/.test(elem.innerText)) {
                info.likes = elem.innerText.trim();
                break;
            }
        }
        
        // 提取评论数
        const commentSelectors = [
            '[data-e2e="comment-count"]',
            '[class*="comment-count"]',
            '[class*="CommentCount"]',
            'span[class*="comment"]'
        ];
        for (const selector of commentSelectors) {
            const elem = document.querySelector(selector);
            if (elem && elem.innerText.trim() && /\d/.test(elem.innerText)) {
                info.comments = elem.innerText.trim();
                break;
            }
        }
        
        // 提取分享数
        const shareSelectors = [
            '[data-e2e="share-count"]',
            '[class*="share-count"]',
            '[class*="ShareCount"]'
        ];
        for (const selector of shareSelectors) {
            const elem = document.querySelector(selector);
            if (elem && elem.innerText.trim() && /\d/.test(elem.innerText)) {
                info.shares = elem.innerText.trim();
                break;
            }
        }
        
        console.log('[抖音详情] 提取信息:', info);
        return info;
    } catch (e) {
        console.error('[抖音详情] 提取失败:', e);
        return info;
    }
}
"""
