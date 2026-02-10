我将修复搜索功能失效的问题，主要原因是搜索接口 URL 使用了综合搜索 (`/all`) 而非视频垂直搜索 (`/video`)，导致排序和筛选参数可能失效或返回非预期结果。

### 修复计划

1.  **修改搜索 URL 拼接逻辑 (`core/search.py`)**:
    - 将 `https://search.bilibili.com/all` 更改为 `https://search.bilibili.com/video`。
    - 确保 `order` (排序) 和 `duration` (时长) 参数能正确生效。

2.  **增强选择器兼容性 (`core/selectors.py`)**:
    - 更新视频卡片选择器，增加 `.video-item`, `.video-list-item` 等备选类名，以应对 Bilibili 页面结构变化。
    - 更新视频链接选择器，增加更多匹配模式。

3.  **消除硬编码选择器 (`core/search.py`)**:
    - 将代码中残留的硬编码 `.bili-video-card` 替换为统一管理的 `BilibiliSelectors`，确保维护性。

这将确保搜索功能在各种参数组合下都能正常工作，并提高对页面改版的适应性。