import base64

_ENC_KEY = b"bili-comment-assistant-v1"


def _xor_encrypt(text: str) -> str:
    text_bytes = text.encode("utf-8")
    key_bytes = _ENC_KEY
    result = bytes(a ^ b for a, b in zip(text_bytes, (key_bytes * ((len(text_bytes) // len(key_bytes)) + 1))[:len(text_bytes)]))
    return base64.b64encode(result).decode("utf-8")


def _xor_decrypt(encrypted: str) -> str:
    try:
        decoded = base64.b64decode(encrypted.encode("utf-8"))
        key_bytes = _ENC_KEY
        result = bytes(a ^ b for a, b in zip(decoded, (key_bytes * ((len(decoded) // len(key_bytes)) + 1))[:len(decoded)]))
        return result.decode("utf-8")
    except Exception:
        return encrypted


def encrypt_api_key(api_key: str) -> str:
    if not api_key or api_key.startswith("ENC:"):
        return api_key
    return f"ENC:{_xor_encrypt(api_key)}"


def decrypt_api_key(api_key: str) -> str:
    if not api_key:
        return ""
    if api_key.startswith("ENC:"):
        return _xor_decrypt(api_key[4:])
    return api_key


if __name__ == "__main__":
    key = input("请输入要加密的 API Key: ").strip()
    if key:
        encrypted = encrypt_api_key(key)
        print(f"\n加密后的字符串:")
        print(encrypted)
        print(f"\n解密验证: {decrypt_api_key(encrypted)}")
