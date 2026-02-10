# GitHub 部署指南

## 步骤 1: 在GitHub上创建仓库

1. 登录到您的GitHub账户
2. 点击右上角的 "+" 图标，选择 "New repository"
3. 填写仓库信息：
   - **Repository name**: `bili-comment-assistant`
   - **Description**: `Bilibili自动评论助手 - 基于Python的B站自动评论工具，支持GUI界面和配置文件管理`
   - 选择 **Public**（公开）或 **Private**（私有）
   - **不要**勾选 "Initialize this repository with a README"（因为我们已经有了README.md）
   - **不要**添加 .gitignore 或 license（因为我们已经有了.gitignore）

4. 点击 "Create repository"

## 步骤 2: 添加远程仓库并推送代码

在本地项目目录中执行以下命令：

```bash
# 添加远程仓库（将 YOUR_USERNAME 替换为您的GitHub用户名）
git remote add origin https://