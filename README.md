# Bilibili 自动评论助手

一个基于Python的B站自动评论工具，支持GUI界面和配置文件管理。

## 功能特性

- 🎯 **智能搜索**：根据关键词搜索B站视频
- 💬 **自动评论**：支持文本和图片评论
- 🔐 **Cookie认证**：使用B站Cookie进行登录
- 📊 **历史记录**：记录已评论的视频，避免重复评论
- 🖥️ **GUI界面**：友好的图形用户界面
- ⚙️ **配置文件**：YAML格式配置文件，易于定制

## 项目结构

```
bili-comment-assistant/
├── core/                    # 核心功能模块
│   ├── auth.py             # 认证管理
│   ├── comment.py          # 评论管理
│   ├── history.py          # 历史记录管理
│   ├── search.py           # 搜索管理
│   └── __init__.py
├── utils/                  # 工具模块
│   ├── logger.py           # 日志工具
│   └── __init__.py
├── assets/                 # 资源文件
├── logs/                   # 日志目录
├── config.yaml            # 配置文件
├── gui.py                 # GUI界面
├── main.py                # 主程序
├── requirements.txt       # 依赖列表
└── README.md             # 说明文档
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 配置Cookie
1. 登录B站网页版
2. 使用浏览器开发者工具获取Cookie
3. 将Cookie保存到`cookies.json`文件

### 2. 编辑配置文件
编辑`config.yaml`文件，配置搜索关键词、评论内容等参数。

### 3. 运行程序
```bash
# 运行GUI版本
python gui.py

# 或运行命令行版本
python main.py
```

## 配置文件说明

```yaml
account:
  cookie_file: cookies.json  # Cookie文件路径

search:
  keywords:                  # 搜索关键词列表
  - "测试"
  max_videos_per_keyword: 5  # 每个关键词最多搜索的视频数

comment:
  texts:                    # 评论文本列表
  - "感谢分享，很有帮助！"
  images:                   # 评论图片列表
  - "path/to/image.png"

behavior:
  min_delay: 1.0           # 最小延迟（秒）
  max_delay: 5.0           # 最大延迟（秒）
  headless: false          # 是否无头模式
  timeout: 30000           # 超时时间（毫秒）
```

## 注意事项

1. **遵守平台规则**：请合理使用，避免频繁操作导致账号异常
2. **保护隐私**：不要泄露Cookie等敏感信息
3. **合法使用**：仅用于学习和测试目的

## 许可证

本项目仅供学习和研究使用，请遵守相关法律法规和平台规则。

## 贡献

欢迎提交Issue和Pull Request来改进本项目。