# 新的视频提取JavaScript代码
# 基于实际HTML结构：使用 waterfall_item_ ID 和 search-result-card

EXTRACT_VIDEOS_JS = """
(maxCount) => {
    const videos = [];
    const seenIds = new Set();
    
    // 查找所有视频卡片
    const cards = document.querySelectorAll('.search-result-card');
    console.log('[抖音提取] 找到卡片数量:', cards.length);
    
    for (const card of cards) {
        if (videos.length >= maxCount) break;
        
        try {
            // 获取父容器的ID（包含视频ID）
            const container = card.closest('[id^="waterfall_item_"]');
            if (!container) {
                console.log('[抖音提取] 卡片没有waterfall_item容器');
                continue;
            }
            
            const containerId = container.id;
            // 提取视频ID：waterfall_item_7607670496607657958 -> 7607670496607657958
            const videoId = containerId.replace('waterfall_item_', '');
            
            if (!videoId || seenIds.has(videoId)) continue;
            seenIds.add(videoId);
            
            // 构造视频URL
            const url = `https://www.douyin.com/video/${videoId}`;
            
            // 获取标题（多个可能的class）
            const titleSelectors = ['.vqtFIVjM', '[class*="title"]', '[class*="Title"]'];
            let title = 'Unknown';
            for (const selector of titleSelectors) {
                const elem = card.querySelector(selector);
                if (elem && elem.innerText.trim()) {
                    title = elem.innerText.trim();
                    break;
                }
            }
            
            // 获取作者（多个可能的class）
            const authorSelectors = ['.VikzymRj', '[class*="author"]', '[class*="Author"]'];
            let author = 'Unknown';
            for (const selector of authorSelectors) {
                const elem = card.querySelector(selector);
                if (elem && elem.innerText.trim()) {
                    author = elem.innerText.trim();
                    break;
                }
            }
            
            videos.push({
                url: url,
                title: title,
                author: author
            });
            
            console.log('[抖音提取] 成功提取:', videoId, title.substring(0, 30));
        } catch (e) {
            console.error('[抖音提取] 提取卡片失败:', e);
        }
    }
    
    console.log('[抖音提取] 总共提取:', videos.length, '个视频');
    return videos;
}
"""
