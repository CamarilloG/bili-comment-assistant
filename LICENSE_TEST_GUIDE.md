# License 验证系统 - 快速测试指南

## ✅ 系统已完成并测试通过

License 验证系统已经完全集成到启动流程中，并且支持两种模式：

### 模式一：GUI 模式（推荐）
- 需要 tkinter 支持
- 提供友好的图形界面
- 支持文件选择和拖拽

### 模式二：命令行模式（自动降级）
- 当 tkinter 不可用时自动启用
- 纯文本界面
- 自动检测 license 文件
- 支持手动输入路径

## 🧪 测试结果

已测试启动流程，验证成功：

```
[License] 警告: tkinter 不可用，将使用命令行模式

==================================================
  B站评论助手 - License 验证
==================================================

[*] 找到 License 文件: ./license.lic

[*] 正在验证 License...

[√] 验证成功!

License 信息:
  用户: test@example.com
  类型: 测试版
  有效期: 永久
  备注: 测试用 License

[*] 正在启动程序...
```

## 📝 使用说明

### 用户端使用

1. **获取 License 文件**
   - 从发行方获取 `license.lic` 文件

2. **放置 License 文件**
   - 将 `license.lic` 放在 exe 同目录下（推荐）
   - 或放在以下任一位置：
     - `./license.lic`
     - `./License.lic`
     - `exe所在目录/license.lic`

3. **启动程序**
   - 运行 `start.bat`
   - 程序会自动验证 License
   - 验证成功后自动启动主程序

### 发行方使用

#### 方式一：使用批处理脚本（推荐）

双击运行 `generate_license.bat`：

```
请选择操作:
  1. 生成密钥对
  2. 生成永久授权 License
  3. 生成时间限制 License
  4. 退出
```

#### 方式二：使用命令行

```bash
# 生成永久授权
python tools/license_generator.py generate \
  -k keys/private_key.pem \
  -u "customer@example.com" \
  -t "专业版" \
  -n "给某某公司的授权" \
  -o customer_license.lic

# 生成30天试用授权
python tools/license_generator.py generate \
  -k keys/private_key.pem \
  -u "trial@example.com" \
  -t "试用版" \
  -d 30 \
  -n "30天试用" \
  -o trial_license.lic
```

## 🔐 安全提示

### 已生成的密钥对

- **私钥**: `keys/private_key.pem` ⚠️ 请妥善保管，不要泄露
- **公钥**: `keys/public_key.pem` ✅ 已嵌入程序

### 重要提醒

1. ⚠️ 私钥文件不要提交到代码仓库（已添加 .gitignore）
2. ⚠️ 建议将私钥备份到安全的地方
3. ⚠️ 如果私钥泄露，需要重新生成密钥对并重新签发所有 license
4. ✅ 公钥已经嵌入到 `app/license/validator.py`，无需额外配置

## 📦 打包说明

使用 PyInstaller 打包时，确保包含 license 模块：

```python
# 在 .spec 文件中添加
datas=[
    ('app/license', 'license'),
],
hiddenimports=[
    'cryptography',
],
```

注意：
- tkinter 通常会被 PyInstaller 自动包含
- 如果打包后 tkinter 不可用，程序会自动降级到命令行模式
- 命令行模式功能完整，只是没有图形界面

## 🎯 验证流程

1. **程序启动**
   - 执行 `run_web.py`

2. **License 验证**
   - 自动检测 tkinter 是否可用
   - 如果可用：显示 GUI 验证窗口
   - 如果不可用：使用命令行模式

3. **自动查找 License**
   - 检查 `./license.lic`
   - 检查 `./License.lic`
   - 检查 `exe所在目录/license.lic`

4. **验证 License**
   - 验证签名
   - 检查过期时间
   - 验证数据完整性

5. **启动主程序**
   - 验证成功：继续启动
   - 验证失败：停止启动并显示错误

## ❓ 常见问题

### Q: 提示 "tkinter 不可用" 怎么办？
A: 这是正常的，程序会自动使用命令行模式，功能完全相同。

### Q: 如何测试验证功能？
A: 直接运行 `start.bat`，程序会自动进行验证。

### Q: 验证失败怎么办？
A: 检查以下几点：
1. license.lic 文件是否存在
2. 文件是否被修改或损坏
3. 是否已过期
4. 联系发行方获取新的 license

### Q: 可以跳过验证吗？
A: 不可以，这是设计的安全特性。如需测试，可以使用已生成的测试 license。

## 📁 相关文件

- `app/license/validator.py` - 验证逻辑
- `app/license/gui.py` - GUI 和命令行界面
- `app/run_web.py` - 启动入口（已集成验证）
- `tools/license_generator.py` - License 生成工具
- `generate_license.bat` - Windows 批处理工具
- `keys/private_key.pem` - 私钥（请保密）
- `keys/public_key.pem` - 公钥（已嵌入程序）
- `app/license.lic` - 测试 license

## ✨ 特性总结

- ✅ 完全离线验证
- ✅ RSA 2048 位加密
- ✅ 支持 GUI 和命令行两种模式
- ✅ 自动检测 license 文件
- ✅ 友好的错误提示
- ✅ 支持永久和时间限制授权
- ✅ 已集成到启动流程
- ✅ 测试通过，可以直接使用

## 🎉 完成状态

所有功能已实现并测试通过，系统可以直接投入使用！
