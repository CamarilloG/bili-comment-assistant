# License 验证系统使用说明

## 概述

本系统为 B 站评论助手添加了离线 License 验证功能，使用 RSA 非对称加密确保 License 的安全性和不可篡改性。

## 特性

- ✅ 完全离线验证，无需联网
- ✅ RSA 2048 位非对称加密
- ✅ 支持永久授权和时间限制授权
- ✅ 友好的 GUI 验证界面
- ✅ 支持文件选择和拖拽
- ✅ 自动检测固定路径的 license 文件

## 目录结构

```
bili-bot/
├── app/
│   ├── license/              # License 验证模块
│   │   ├── __init__.py
│   │   ├── validator.py      # 验证逻辑
│   │   └── gui.py            # GUI 界面
│   └── run_web.py            # 启动入口（已集成验证）
├── tools/
│   └── license_generator.py  # License 生成工具
└── keys/                     # 密钥存放目录（需自行创建）
    ├── private_key.pem       # 私钥（不要提交到仓库）
    └── public_key.pem        # 公钥
```

## 使用流程

### 第一步：生成密钥对

首次使用需要生成 RSA 密钥对：

```bash
cd F:\AI+program\bili-bot
python tools/license_generator.py keygen -o keys
```

这将在 `keys` 目录下生成：
- `private_key.pem` - 私钥（用于签名 license，请妥善保管）
- `public_key.pem` - 公钥（用于验证 license，需要嵌入程序）

**重要提示：**
1. 私钥文件不要提交到代码仓库
2. 建议将私钥备份到安全的地方
3. 如果私钥泄露，需要重新生成密钥对并重新签发所有 license

### 第二步：将公钥嵌入程序

打开 `app/license/validator.py`，找到 `PUBLIC_KEY_PEM` 变量，将 `keys/public_key.pem` 的内容复制进去：

```python
PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
（这里粘贴 public_key.pem 的完整内容）
...
-----END PUBLIC KEY-----"""
```

### 第三步：生成 License 文件

使用 license_generator.py 生成 license 文件：

#### 生成永久授权

```bash
python tools/license_generator.py generate \
  -k keys/private_key.pem \
  -u "user@example.com" \
  -t "专业版" \
  -n "给某某公司的授权" \
  -o license.lic
```

#### 生成时间限制授权

```bash
python tools/license_generator.py generate \
  -k keys/private_key.pem \
  -u "user@example.com" \
  -t "试用版" \
  -d 30 \
  -n "30天试用授权" \
  -o license_trial.lic
```

参数说明：
- `-k, --key`: 私钥文件路径（必需）
- `-u, --user`: 用户标识，如邮箱或昵称（必需）
- `-t, --type`: 授权类型，如"标准版"、"专业版"（默认：标准版）
- `-d, --days`: 有效天数，不指定则为永久授权
- `-n, --notes`: 备注信息
- `-o, --output`: 输出文件路径（默认：license.lic）

### 第四步：分发 License

将生成的 `.lic` 文件发送给用户。用户可以：
1. 将 license.lic 放在 exe 同目录下（推荐）
2. 启动程序时手动选择 license 文件
3. 拖拽 license 文件到验证窗口

## License 文件格式

License 文件是 JSON 格式，包含两部分：

```json
{
  "data": "{...}",      // license 数据（JSON 字符串）
  "signature": "..."    // RSA 签名（Base64 编码）
}
```

其中 data 字段包含：

```json
{
  "user": "user@example.com",           // 用户标识
  "type": "专业版",                      // 授权类型
  "notes": "给某某公司的授权",            // 备注
  "issue_date": "2026-02-27T...",       // 签发时间
  "expire_date": "2027-02-27T..."       // 过期时间（空字符串表示永久）
}
```

## 验证流程

1. 程序启动时自动显示 License 验证窗口
2. 自动尝试从以下路径加载 license：
   - `./license.lic`
   - `./License.lic`
   - `exe所在目录/license.lic`
3. 如果找到 license 文件，自动进行验证
4. 验证通过后，关闭验证窗口，启动主程序
5. 验证失败时，显示错误信息，不启动主程序

## 安全性说明

### 已实现的安全措施

1. **非对称加密**：使用 RSA 2048 位密钥，私钥不出现在程序中
2. **数字签名**：使用 PSS 填充模式，防止签名伪造
3. **完整性校验**：任何对 license 内容的修改都会导致签名验证失败
4. **时间验证**：支持过期时间检查

### 潜在风险

1. **公钥可见**：公钥嵌入在程序中，可以被提取
2. **验证逻辑可见**：Python 代码可以被反编译
3. **内存补丁**：运行时可以通过内存修改绕过验证

### 建议的额外措施

1. 使用 PyInstaller 打包时启用代码混淆
2. 定期更换密钥对
3. 对重要客户使用硬件绑定（MAC 地址、硬盘序列号等）
4. 添加在线激活验证（可选）

## 常见问题

### Q: 如何更新 license？

A: 重新生成 license 文件并替换旧文件即可，无需重启程序。

### Q: 如果私钥丢失怎么办？

A: 需要重新生成密钥对，并重新签发所有 license。旧的 license 将无法使用。

### Q: 可以给同一个用户生成多个 license 吗？

A: 可以，每个 license 都是独立的。

### Q: 如何撤销已发出的 license？

A: 当前版本不支持撤销。如需撤销，需要更换密钥对并重新打包程序。

### Q: 验证失败的常见原因？

A:
1. license 文件被修改或损坏
2. license 已过期
3. 公钥与签名 license 的私钥不匹配
4. license 文件格式错误

## 开发测试

### 测试验证模块

```bash
cd F:\AI+program\bili-bot\app
python -m license.gui
```

### 测试生成工具

```bash
cd F:\AI+program\bili-bot
python tools/license_generator.py --help
```

## 依赖库

需要安装以下 Python 库：

```bash
pip install cryptography
pip install tkinterdnd2  # 可选，用于拖拽功能
```

如果不安装 tkinterdnd2，GUI 仍然可以正常工作，只是不支持拖拽功能。

## 打包注意事项

使用 PyInstaller 打包时，需要确保包含以下文件：

```python
# 在 .spec 文件中添加
datas=[
    ('app/license', 'license'),
],
hiddenimports=[
    'cryptography',
    'tkinterdnd2',
],
```

## 更新日志

### v1.0.0 (2026-02-27)
- 初始版本
- 实现基础的 RSA 签名验证
- 实现 GUI 验证界面
- 实现 license 生成工具
