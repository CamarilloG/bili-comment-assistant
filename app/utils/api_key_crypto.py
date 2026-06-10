"""
简单的 API Key 加密/解密工具

使用 base64 + XOR 简单加密，避免明文存储敏感信息。
注意：这不是强加密，只是防止明文泄露。
"""

import base64
import os


def _get_machine_key() -> bytes:
    """
    获取机器特征密钥
    使用机器名 + 用户名作为密钥基础
    """
    import platform
    import getpass

    machine_id = f"{platform.node()}-{getpass.getuser()}"
    # 扩展到 32 字节
    key = (machine_id * 32)[:32].encode('utf-8')
    return key


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    """XOR 加密/解密"""
    return bytes(a ^ b for a, b in zip(data, key * (len(data) // len(key) + 1)))


def encode_api_key(plain_key: str) -> str:
    """
    加密 API key

    Args:
        plain_key: 明文 API key

    Returns:
        加密后的 base64 字符串，格式: "enc:base64_string"
    """
    if not plain_key or plain_key.strip() == "":
        return ""

    # 已经加密过的不再加密
    if plain_key.startswith("enc:"):
        return plain_key

    try:
        key = _get_machine_key()
        plain_bytes = plain_key.encode('utf-8')
        encrypted = _xor_bytes(plain_bytes, key)
        encoded = base64.b64encode(encrypted).decode('ascii')
        return f"enc:{encoded}"
    except Exception as e:
        # 加密失败返回原文（降级处理）
        print(f"API key 加密失败: {e}")
        return plain_key


def decode_api_key(encoded_key: str) -> str:
    """
    解密 API key

    Args:
        encoded_key: 加密的 API key (格式: "enc:base64_string") 或明文

    Returns:
        解密后的明文 API key
    """
    if not encoded_key or encoded_key.strip() == "":
        return ""

    # 如果不是加密格式，直接返回（兼容旧配置）
    if not encoded_key.startswith("enc:"):
        return encoded_key

    try:
        # 去掉 "enc:" 前缀
        encoded = encoded_key[4:]
        key = _get_machine_key()
        encrypted = base64.b64decode(encoded)
        plain_bytes = _xor_bytes(encrypted, key)
        result = plain_bytes.decode('utf-8')

        # 验证解密结果是否合理（不包含控制字符）
        if all(32 <= ord(c) <= 126 or c in '\t\n\r' for c in result):
            return result
        else:
            # 解密结果包含非打印字符，可能是旧格式，尝试简单 base64
            raise ValueError("Invalid decryption result")

    except Exception as e:
        # 解密失败，尝试简单 base64 解码（兼容旧格式）
        try:
            encoded = encoded_key[4:]
            return base64.b64decode(encoded).decode('utf-8')
        except Exception:
            # 都失败了，返回原文（降级处理）
            print(f"API key 解密失败: {e}")
            return encoded_key


def is_encrypted(key: str) -> bool:
    """
    判断 API key 是否已加密

    Args:
        key: API key 字符串

    Returns:
        True 如果已加密，False 如果是明文
    """
    return key.startswith("enc:") if key else False


if __name__ == "__main__":
    # 测试
    test_keys = [
        "sk-1234567890abcdef",
        "YOUR_API_KEY_HERE",
        "",
        "enc:already_encrypted",
    ]

    print("=" * 80)
    print("API Key 加密/解密测试")
    print("=" * 80)

    for plain in test_keys:
        print(f"\n原始: {plain}")
        encrypted = encode_api_key(plain)
        print(f"加密: {encrypted}")
        decrypted = decode_api_key(encrypted)
        print(f"解密: {decrypted}")
        print(f"验证: {'OK' if decrypted == plain else 'FAIL'}")
