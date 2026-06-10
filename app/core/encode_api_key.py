"""
API Key 加密工具（已废弃，请使用 utils.api_key_crypto）

保留此文件用于向后兼容。
新代码请使用 utils.api_key_crypto.encode_api_key() 和 decode_api_key()
"""
import base64
import sys


def encode(plain: str) -> str:
    """简单 base64 编码（已废弃）"""
    return "enc:" + base64.b64encode(plain.strip().encode("utf-8")).decode("ascii")


def main() -> None:
    """命令行工具：加密 API key"""
    if len(sys.argv) > 1:
        plain = " ".join(sys.argv[1:]).strip()
    else:
        plain = (sys.stdin.read() or "").strip()
    if not plain:
        print("用法: python -m app.core.encode_api_key <明文 api_key>", file=sys.stderr)
        print("  或: echo 明文key | python -m app.core.encode_api_key", file=sys.stderr)
        print("\n注意: 此工具已废弃，建议使用 utils.api_key_crypto", file=sys.stderr)
        sys.exit(1)

    # 使用新的加密方法
    try:
        from utils.api_key_crypto import encode_api_key
        encrypted = encode_api_key(plain)
        print(encrypted)
    except ImportError:
        # 降级到简单 base64
        print(encode(plain))


if __name__ == "__main__":
    main()
