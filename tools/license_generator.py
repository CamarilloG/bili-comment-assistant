"""
License 生成工具
用于生成和签名 license 文件
"""
import json
import base64
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("错误: 需要安装 cryptography 库")
    print("请运行: pip install cryptography")
    exit(1)


class LicenseGenerator:
    """License 生成器"""

    def __init__(self, private_key_path: str):
        """
        初始化生成器

        Args:
            private_key_path: 私钥文件路径
        """
        self.private_key_path = private_key_path
        self._load_private_key()

    def _load_private_key(self):
        """加载私钥"""
        try:
            with open(self.private_key_path, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
        except FileNotFoundError:
            raise FileNotFoundError(f"私钥文件不存在: {self.private_key_path}")
        except Exception as e:
            raise ValueError(f"加载私钥失败: {e}")

    def generate_license(
        self,
        user: str,
        license_type: str = "标准版",
        expire_days: Optional[int] = None,
        notes: str = ""
    ) -> str:
        """
        生成 license

        Args:
            user: 用户标识（邮箱或昵称）
            license_type: 授权类型
            expire_days: 有效天数（None 表示永久）
            notes: 备注信息

        Returns:
            license JSON 字符串
        """
        # 构建 license 数据
        data = {
            "user": user,
            "type": license_type,
            "notes": notes,
            "issue_date": datetime.now().isoformat(),
        }

        # 添加过期时间
        if expire_days is not None:
            expire_date = datetime.now() + timedelta(days=expire_days)
            data["expire_date"] = expire_date.isoformat()
        else:
            data["expire_date"] = ""  # 空字符串表示永久

        # 转换为 JSON 字符串
        data_str = json.dumps(data, ensure_ascii=False, indent=2)

        # 签名
        signature = self._sign_data(data_str)
        signature_b64 = base64.b64encode(signature).decode('utf-8')

        # 构建最终 license
        license_data = {
            "data": data_str,
            "signature": signature_b64
        }

        return json.dumps(license_data, ensure_ascii=False, indent=2)

    def _sign_data(self, data_str: str) -> bytes:
        """对数据进行签名"""
        signature = self.private_key.sign(
            data_str.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature

    def save_license(self, license_content: str, output_path: str):
        """保存 license 到文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(license_content)


def generate_keypair(output_dir: str = "."):
    """
    生成 RSA 密钥对

    Args:
        output_dir: 输出目录
    """
    print("正在生成 RSA 密钥对...")

    # 生成私钥
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # 生成公钥
    public_key = private_key.public_key()

    # 保存私钥
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    private_key_path = Path(output_dir) / "private_key.pem"
    with open(private_key_path, 'wb') as f:
        f.write(private_pem)

    # 保存公钥
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    public_key_path = Path(output_dir) / "public_key.pem"
    with open(public_key_path, 'wb') as f:
        f.write(public_pem)

    print(f"密钥对生成成功!")
    print(f"   私钥: {private_key_path.absolute()}")
    print(f"   公钥: {public_key_path.absolute()}")
    print()
    print("重要提示:")
    print("   1. 私钥 (private_key.pem) 请妥善保管，不要泄露或提交到代码仓库")
    print("   2. 公钥 (public_key.pem) 需要复制到程序的 license/validator.py 中")
    print("   3. 建议将私钥备份到安全的地方")


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="License 生成工具")
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # 生成密钥对命令
    keygen_parser = subparsers.add_parser('keygen', help='生成 RSA 密钥对')
    keygen_parser.add_argument(
        '-o', '--output',
        default='.',
        help='输出目录（默认: 当前目录）'
    )

    # 生成 license 命令
    generate_parser = subparsers.add_parser('generate', help='生成 License 文件')
    generate_parser.add_argument(
        '-k', '--key',
        required=True,
        help='私钥文件路径'
    )
    generate_parser.add_argument(
        '-u', '--user',
        required=True,
        help='用户标识（邮箱或昵称）'
    )
    generate_parser.add_argument(
        '-t', '--type',
        default='标准版',
        help='授权类型（默认: 标准版）'
    )
    generate_parser.add_argument(
        '-d', '--days',
        type=int,
        help='有效天数（不指定则为永久授权）'
    )
    generate_parser.add_argument(
        '-n', '--notes',
        default='',
        help='备注信息'
    )
    generate_parser.add_argument(
        '-o', '--output',
        default='license.lic',
        help='输出文件路径（默认: license.lic）'
    )

    args = parser.parse_args()

    if args.command == 'keygen':
        generate_keypair(args.output)

    elif args.command == 'generate':
        try:
            generator = LicenseGenerator(args.key)
            license_content = generator.generate_license(
                user=args.user,
                license_type=args.type,
                expire_days=args.days,
                notes=args.notes
            )
            generator.save_license(license_content, args.output)

            print(f"License 生成成功!")
            print(f"   输出文件: {Path(args.output).absolute()}")
            print()
            print("License 信息:")
            print(f"   用户: {args.user}")
            print(f"   类型: {args.type}")
            if args.days:
                expire_date = datetime.now() + timedelta(days=args.days)
                print(f"   有效期: {args.days} 天（到期时间: {expire_date.strftime('%Y-%m-%d')}）")
            else:
                print(f"   有效期: 永久")
            if args.notes:
                print(f"   备注: {args.notes}")

        except Exception as e:
            print(f"生成失败: {e}")
            exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
