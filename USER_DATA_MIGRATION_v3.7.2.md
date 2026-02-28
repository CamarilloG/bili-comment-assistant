# 用户数据目录迁移说明 - v3.7.2

## 变更说明

从 v3.7.2 版本开始，所有配置文件、日志文件和用户数据都存储在软件根目录下的 **"用户数据"** 文件夹中，不再使用临时文件或 app 目录。

---

## 目录结构

### 新的存储结构

```
软件根目录/
├── BiliBotLauncher_v3.7.2.exe    # 启动器
├── python/                        # Python 运行环境
├── license.lic                    # License 文件
└── 用户数据/                      # 所有用户数据（新增）
    ├── config.yaml                # 实例 0 配置文件
    ├── cookies.json               # 实例 0 Cookie
    ├── history.json               # 实例 0 历史记录
    ├── comment_log.csv            # 实例 0 评论日志
    ├── captcha_record.json        # 验证码记录
    ├── login_qrcode.png           # 登录二维码（临时）
    ├── logs/                      # 日志文件夹
    │   └── bili_bot_2026-02-28.log
    └── instances/                 # 多实例数据
        ├── 1/                     # 实例 1
        │   ├── config.yaml
        │   ├── cookies.json
        │   ├── history.json
        │   └── comment_log.csv
        ├── 2/                     # 实例 2
        │   └── ...
        └── ...
```

### 旧的存储结构（v3.7.1 及之前）

```
软件根目录/
├── BiliBotLauncher_v3.7.1.exe
├── python/
├── app/                           # 旧位置
│   ├── config.yaml                # 实例 0 配置
│   ├── cookies.json               # 实例 0 Cookie
│   ├── history.json               # 实例 0 历史
│   ├── comment_log.csv            # 实例 0 日志
│   └── instances/                 # 多实例
│       └── 1/
│           └── ...
└── logs/                          # 旧日志位置
    └── bili_bot_2026-02-28.log
```

---

## 变更详情

### 1. 配置文件位置

**实例 0（主实例）：**
- 旧位置：`app/config.yaml`
- 新位置：`用户数据/config.yaml`

**其他实例：**
- 旧位置：`app/instances/<实例ID>/config.yaml`
- 新位置：`用户数据/instances/<实例ID>/config.yaml`

### 2. Cookie 文件位置

**实例 0：**
- 旧位置：`app/cookies.json`
- 新位置：`用户数据/cookies.json`

**其他实例：**
- 旧位置：`app/instances/<实例ID>/cookies.json`
- 新位置：`用户数据/instances/<实例ID>/cookies.json`

### 3. 历史记录位置

**实例 0：**
- 旧位置：`app/history.json`
- 新位置：`用户数据/history.json`

**其他实例：**
- 旧位置：`app/instances/<实例ID>/history.json`
- 新位置：`用户数据/instances/<实例ID>/history.json`

### 4. 评论日志位置

**实例 0：**
- 旧位置：`app/comment_log.csv`
- 新位置：`用户数据/comment_log.csv`

**其他实例：**
- 旧位置：`app/instances/<实例ID>/comment_log.csv`
- 新位置：`用户数据/instances/<实例ID>/comment_log.csv`

### 5. 日志文件位置

- 旧位置：`logs/bili_bot_*.log`
- 新位置：`用户数据/logs/bili_bot_*.log`

### 6. 验证码记录位置

- 旧位置：`app/captcha_record.json`
- 新位置：`用户数据/captcha_record.json`

---

## 升级迁移指南

### 从 v3.7.1 升级到 v3.7.2

#### 方法 1：手动迁移（推荐）

1. **备份旧数据**：
   ```
   备份 app/config.yaml
   备份 app/cookies.json
   备份 app/history.json
   备份 app/comment_log.csv
   备份 app/instances/ 目录（如果有多实例）
   ```

2. **安装新版本**：
   - 替换 `BiliBotLauncher_v3.7.2.exe`

3. **首次启动**：
   - 启动程序，会自动创建 `用户数据` 文件夹

4. **迁移数据**：
   ```
   复制 app/config.yaml → 用户数据/config.yaml
   复制 app/cookies.json → 用户数据/cookies.json
   复制 app/history.json → 用户数据/history.json
   复制 app/comment_log.csv → 用户数据/comment_log.csv
   复制 app/instances/ → 用户数据/instances/（如果有）
   ```

5. **验证**：
   - 重启程序
   - 检查配置是否正常加载
   - 检查 Cookie 是否有效

#### 方法 2：全新安装

1. **导出配置**：
   - 在旧版本中导出配置（如果有导出功能）
   - 或手动记录配置内容

2. **安装新版本**：
   - 解压新版本到新目录

3. **重新配置**：
   - 启动程序
   - 重新配置所有设置
   - 重新登录账号

---

## 优势

### 1. 数据集中管理

所有用户数据集中在 `用户数据` 文件夹，方便：
- 备份：只需备份一个文件夹
- 迁移：复制整个文件夹即可
- 清理：删除文件夹即可清空所有数据

### 2. 避免权限问题

不再使用临时文件或系统目录，避免：
- 权限不足导致的写入失败
- 临时文件被系统清理
- 多用户环境下的数据冲突

### 3. 便于打包分发

- 用户数据与程序分离
- 更新程序时不会影响用户数据
- 便于制作绿色便携版

### 4. 支持多实例

- 每个实例的数据独立存储
- 实例间互不干扰
- 便于管理和备份

---

## 注意事项

### 1. 首次启动

首次启动 v3.7.2 时：
- 会自动创建 `用户数据` 文件夹
- 不会自动迁移旧数据
- 需要手动迁移或重新配置

### 2. 旧数据保留

升级后：
- 旧的 `app/` 目录数据不会被删除
- 可以手动删除旧数据
- 建议先备份再删除

### 3. 多实例用户

如果使用了多实例：
- 需要迁移 `app/instances/` 整个目录
- 保持目录结构不变
- 确保所有实例数据完整

### 4. 日志文件

旧的日志文件：
- 保留在 `logs/` 目录
- 新日志写入 `用户数据/logs/`
- 可以手动合并或删除旧日志

---

## 技术细节

### 代码变更

**修改的文件：**

1. **app/core/slot.py**
   - 添加 `get_user_data_dir()` 函数
   - 修改 `get_workdir()` 使用用户数据目录
   - 修改 `list_slot_ids()` 扫描用户数据目录

2. **app/utils/logger.py**
   - 修改日志目录为 `用户数据/logs/`
   - 自动创建日志目录

3. **app/core/captcha_tracker.py**
   - 修改默认文件路径为 `用户数据/captcha_record.json`

### 路径获取逻辑

```python
# 获取软件根目录
if getattr(sys, "frozen", False):
    # 打包后：exe 所在目录
    root = os.path.dirname(sys.executable)
else:
    # 开发环境：项目根目录
    root = os.path.abspath(os.path.join(__file__, "..", ".."))

# 用户数据目录
user_data_dir = os.path.join(root, "用户数据")
```

---

## 常见问题

### Q1: 升级后找不到配置文件？

**A:** 新版本使用 `用户数据` 文件夹，需要手动迁移旧配置：
```
复制 app/config.yaml → 用户数据/config.yaml
```

### Q2: 升级后需要重新登录？

**A:** 需要迁移 Cookie 文件：
```
复制 app/cookies.json → 用户数据/cookies.json
```

### Q3: 历史记录丢失了？

**A:** 需要迁移历史文件：
```
复制 app/history.json → 用户数据/history.json
```

### Q4: 多实例数据如何迁移？

**A:** 复制整个 instances 目录：
```
复制 app/instances/ → 用户数据/instances/
```

### Q5: 可以删除旧的 app 目录吗？

**A:** 迁移完成并验证无误后可以删除：
- 备份重要数据
- 验证新版本运行正常
- 删除 `app/config.yaml`、`app/cookies.json` 等文件
- 保留 `app/` 目录本身（程序需要）

### Q6: 用户数据文件夹可以改名吗？

**A:** 不建议改名，程序硬编码为 "用户数据"。如需修改需要重新编译。

### Q7: 可以把用户数据放到其他位置吗？

**A:** 当前版本不支持自定义位置，固定在软件根目录下。

---

## 版本信息

- 版本：v3.7.2
- 变更日期：2026-02-28
- 变更类型：数据存储位置优化
- 影响范围：所有用户数据和日志文件

---

## 总结

v3.7.2 版本将所有用户数据集中存储在 `用户数据` 文件夹中，提供了更好的数据管理体验。升级时需要手动迁移旧数据，但迁移过程简单直接。建议所有用户升级到新版本以获得更好的数据管理体验。
