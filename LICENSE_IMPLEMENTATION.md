# License 验证系统 - 实现完成

## ✅ 已完成的功能

### 1. License 验证模块 (`app/license/validator.py`)
- ✅ RSA 公钥验证
- ✅ 数字签名校验
- ✅ 过期时间检查
- ✅ 数据完整性验证
- ✅ 支持永久授权和时间限制授权

### 2. License 验证 GUI (`app/license/gui.py`)
- ✅ 友好的图形界面
- ✅ 支持文件选择
- ✅ 支持拖拽文件（需要 tkinterdnd2）
- ✅ 自动检测固定路径的 license 文件
- ✅ 实时验证反馈
- ✅ 验证成功后自动关闭并启动主程序

### 3. License 生成工具 (`tools/license_generator.py`)
- ✅ 生成 RSA 密钥对
- ✅ 生成永久授权 license
- ✅ 生成时间限制 license
- ✅ 命令行界面
- ✅ 支持自定义用户信息、授权类型、备注等

### 4. 启动流程集成 (`app/run_web.py`)
- ✅ 在程序启动前进行 license 验证
- ✅ 验证失败时阻止程序启动
- ✅ 验证成功后继续正常启动流程

### 5. 辅助工具
- ✅ 批处理脚本 (`generate_license.bat`) - Windows 图形化生成工具
- ✅ 详细使用文档 (`LICENSE_SYSTEM_README.md`)

## 📁 文件结构

```
bili-bot/
├── app/
│   ├── license/
│   │   ├── __init__.py
│   │   ├── validator.py          # 验证逻辑
│   │   └── gui.py                # GUI 界面
│   ├── run_web.py                # 启动入口（已集成验证）
│   └── license.lic               # 测试 license 文件
├── tools/
│   └── license_generator.py      # License 生成工具
├── keys/
│   ├── private_key.pem           # 私钥（已生成）
│   └── public_key.pem            # 公钥（已生成）
├── generate_license.bat          # Windows 批处理工具
└── LICENSE_SYSTEM_README.md      # 详细使用文档
```

## 🚀 快速开始

### 方式一：使用批处理脚本（推荐）

双击运行 `generate_license.bat`，按照提示操作：
1. 首次使用选择"生成密钥对"
2. 之后选择"生成永久授权"或"生成时间限制"
3. 按提示输入用户信息
4. 生成的 license 文件会保存在当前目录

### 方式二：使用命令行

```bash
# 生成密钥对（首次使用）
python tools/license_generator.py keygen -o keys

# 生成永久授权
python tools/license_generator.py generate \
  -k keys/private_key.pem \
  -u "user@example.com" \
  -t "专业版" \
  -o license.lic

# 生成30天试用授权
python tools/license_generator.py generate \
  -k keys/private_key.pem \
  -u "user@example.com" \
  -t "试用版" \
  -d 30 \
  -o license_trial.lic
```

## 🔐 安全性说明

### 已实现的安全措施
1. ✅ RSA 2048 位非对称加密
2. ✅ PSS 填充模式的数字签名
3. ✅ 私钥不出现在程序中
4. ✅ 完整性校验（任何修改都会导致验证失败）
5. ✅ 时间验证（支持过期检查）

### 重要提示
- ⚠️ 私钥文件 (`keys/private_key.pem`) 请妥善保管
- ⚠️ 不要将私钥提交到代码仓库
- ⚠️ 建议将私钥备份到安全的地方
- ⚠️ 如果私钥泄露，需要重新生成密钥对并重新签发所有 license

## 📝 使用流程

### 发行方（你）

1. **生成密钥对**（首次）
   ```bash
   python tools/license_generator.py keygen -o keys
   ```

2. **将公钥嵌入程序**
   - 公钥已经自动嵌入到 `app/license/validator.py`
   - 如果重新生成密钥对，需要手动更新

3. **为用户生成 license**
   ```bash
   python tools/license_generator.py generate \
     -k keys/private_key.pem \
     -u "customer@example.com" \
     -t "专业版" \
     -o customer_license.lic
   ```

4. **将 license 文件发送给用户**

### 用户

1. **获取 license 文件**
   - 从发行方获取 `.lic` 文件

2. **放置 license 文件**
   - 将 `license.lic` 放在 exe 同目录下（推荐）
   - 或启动时手动选择

3. **启动程序**
   - 程序会自动显示验证窗口
   - 验证成功后自动进入主程序

## 🧪 测试

已生成测试 license 文件：
- 文件位置：`app/license.lic`
- 用户：test@example.com
- 类型：测试版
- 有效期：永久

可以直接运行 `start.bat` 测试验证流程。

## 📦 打包注意事项

使用 PyInstaller 打包时，需要确保包含以下内容：

```python
# 在 .spec 文件中添加
datas=[
    ('app/license', 'license'),
],
hiddenimports=[
    'cryptography',
    'tkinter',
    'tkinterdnd2',  # 可选
],
```

## 🔧 依赖库

必需：
```bash
pip install cryptography
```

可选（用于拖拽功能）：
```bash
pip install tkinterdnd2
```

## ❓ 常见问题

### Q: 验证窗口不显示？
A: 检查是否安装了 tkinter（Python 自带）和 cryptography 库。

### Q: 如何撤销已发出的 license？
A: 当前版本不支持撤销。如需撤销，需要更换密钥对并重新打包程序。

### Q: 可以给同一个用户生成多个 license 吗？
A: 可以，每个 license 都是独立的。

### Q: 如何更新 license？
A: 重新生成 license 文件并替换旧文件即可。

## 📚 详细文档

更多详细信息请参考：
- [LICENSE_SYSTEM_README.md](LICENSE_SYSTEM_README.md) - 完整使用文档

## ✨ 特性总结

- ✅ 完全离线验证
- ✅ 安全的 RSA 加密
- ✅ 友好的用户界面
- ✅ 简单的生成工具
- ✅ 灵活的授权方式
- ✅ 详细的文档说明

## 🎉 完成状态

所有需求已完成实现，系统可以直接使用！
