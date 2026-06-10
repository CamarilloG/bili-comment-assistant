"""
License 验证模块
使用 RSA 公钥验证 license 文件的签名和有效性
"""
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend
    from cryptography.exceptions import InvalidSignature
except ImportError:
    raise ImportError("需要安装 cryptography 库: pip install cryptography")


# 内置公钥（PEM 格式）
PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA8BwfSad9JXx0whx9MAoa
pOsBYothm2cY8Oj3DsToOu8Xnh4GBz7HqfwNPguG/fEfEKtAzROfvGKvPErZs4Yq
wVu0d71JxnJlpPXZI+vpuSA3VEQkom+sPb4jnmgS9Oox3m4wbwenfGCyX9Jtk85k
HnNCIfHC9ZnljKLThG/NFBlWL9HTCmF2Jy2hZowZWj0SMUNoxy6upFao/QSDB07h
e7A0580LxZpcKAmp8Z0VBIk4D/J3FkOEneuf2ivVc0+nr6sYGecL7B22MpluEiTA
eY54y61feHsR9TL5sAHOCVRWXqKndHqeabavIYwrsiBgOJDnOoNDiqR3V5uuA1UO
WQIDAQAB
-----END PUBLIC KEY-----"""


class LicenseValidator:
    """License 验证器"""

    def __init__(self, public_key_pem: Optional[str] = None):
        """
        初始化验证器

        Args:
            public_key_pem: 公钥 PEM 字符串，如果为 None 则使用内置公钥
        """
        self.public_key_pem = public_key_pem or PUBLIC_KEY_PEM
        self._load_public_key()

    def _load_public_key(self):
        """加载公钥"""
        try:
            self.public_key = serialization.load_pem_public_key(
                self.public_key_pem.encode('utf-8'),
                backend=default_backend()
            )
        except Exception as e:
            raise ValueError(f"加载公钥失败: {e}")

    def validate_license_file(self, license_path: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        验证 license 文件

        Args:
            license_path: license 文件路径

        Returns:
            (是否有效, 错误信息, license 数据)
        """
        try:
            # 读取文件
            license_file = Path(license_path)
            if not license_file.exists():
                return False, "License 文件不存在", None

            with open(license_file, 'r', encoding='utf-8') as f:
                license_content = f.read()

            # 解析 license
            return self.validate_license_content(license_content)

        except Exception as e:
            return False, f"读取 License 文件失败: {e}", None

    def validate_license_content(self, license_content: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        验证 license 内容

        Args:
            license_content: license 文件内容

        Returns:
            (是否有效, 错误信息, license 数据)
        """
        try:
            # 解析 JSON
            license_data = json.loads(license_content)

            # 检查必需字段
            required_fields = ['data', 'signature']
            for field in required_fields:
                if field not in license_data:
                    return False, f"License 格式错误：缺少 {field} 字段", None

            # 提取数据和签名
            data_str = license_data['data']
            signature_b64 = license_data['signature']

            # 解析数据
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                return False, "License 数据格式错误", None

            # 验证签名
            valid, msg = self._verify_signature(data_str, signature_b64)
            if not valid:
                return False, msg, None

            # 验证数据字段
            valid, msg = self._validate_data_fields(data)
            if not valid:
                return False, msg, None

            # 验证过期时间
            valid, msg = self._check_expiration(data)
            if not valid:
                return False, msg, None

            return True, "验证成功", data

        except json.JSONDecodeError:
            return False, "License 文件格式错误", None
        except Exception as e:
            return False, f"验证失败: {e}", None

    def _verify_signature(self, data_str: str, signature_b64: str) -> Tuple[bool, str]:
        """验证签名"""
        try:
            # 解码签名
            signature = base64.b64decode(signature_b64)

            # 验证签名
            self.public_key.verify(
                signature,
                data_str.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True, ""
        except InvalidSignature:
            return False, "License 签名无效或已被篡改"
        except Exception as e:
            return False, f"签名验证失败: {e}"

    def _validate_data_fields(self, data: Dict) -> Tuple[bool, str]:
        """验证数据字段"""
        # 检查必需字段
        if 'user' not in data:
            return False, "License 缺少用户信息"

        # 可以添加更多字段验证
        return True, ""

    def _check_expiration(self, data: Dict) -> Tuple[bool, str]:
        """检查是否过期"""
        if 'expire_date' not in data:
            # 没有过期时间，视为永久授权
            return True, ""

        expire_date_str = data['expire_date']
        if not expire_date_str:
            # 空字符串，视为永久授权
            return True, ""

        try:
            expire_date = datetime.fromisoformat(expire_date_str)
            now = datetime.now()

            if now > expire_date:
                return False, f"License 已过期（过期时间: {expire_date.strftime('%Y-%m-%d')}）"

            return True, ""
        except ValueError:
            return False, "License 过期时间格式错误"


def validate_license(license_path: str = "./license.lic") -> Tuple[bool, str, Optional[Dict]]:
    """
    便捷函数：验证 license 文件

    Args:
        license_path: license 文件路径

    Returns:
        (是否有效, 错误信息, license 数据)
    """
    validator = LicenseValidator()
    return validator.validate_license_file(license_path)
