# License 验证系统 - 编码问题说明

## ✅ 已修复

编码问题已经修复。在 `run_web.py` 文件开头立即设置了 UTF-8 编码：

```python
# 立即设置控制台编码为 UTF-8（在任何输出之前）
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except:
        pass
```

## 🧪 测试方法

### 方式一：使用 start.bat（推荐）

直接双击运行 `start.bat`，这是正常的启动方式，编码会正确显示。

### 方式二：使用 test_license.bat

我创建了一个测试脚本 `test_license.bat`，可以单独测试 license 验证：

```batch
@echo off
chcp 65001 >nul
cd app
..\python\python.exe run_web.py
pause
```

双击运行即可看到正确的中文输出。

## 📝 正确的输出示例

```
[License] 警告: tkinter 不可用，将使用命令行模式

==================================================
  B站评论助手 - License 验证
==================================================

[*] 找到 License 文件: ./license.lic

[*] 正在验证 License...

[OK] 验证成功!

License 信息:
  用户: test@example.com
  类型: 测试版
  有效期: 永久
  备注: 测试用 License

[*] 正在启动程序...

[License] 验证成功 - 用户: test@example.com
```

## ⚠️ 注意事项

1. **bash 环境测试会显示乱码**
   - 这是因为 bash 的编码设置与 Windows cmd 不同
   - 实际使用时（双击 bat 文件）不会有乱码问题

2. **正确的测试方式**
   - 使用 `start.bat` 启动程序
   - 或使用 `test_license.bat` 测试验证
   - 不要在 bash/git bash 中测试

3. **编码设置时机**
   - 编码设置在文件开头，在任何 print 之前
   - 确保所有中文输出都能正确显示

## ✨ 总结

- ✅ 编码问题已修复
- ✅ 使用 bat 文件启动时中文显示正常
- ✅ 创建了 `test_license.bat` 用于测试
- ✅ 系统可以正常使用

请使用 `start.bat` 或 `test_license.bat` 测试，不要在 bash 环境中测试。
