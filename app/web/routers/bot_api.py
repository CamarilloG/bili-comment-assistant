"""机器人通知 API 路由"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from utils.logger import get_logger
from core.slot import get_config_path
from core.config import ConfigValidator

logger = get_logger()
router = APIRouter()


class BotTestResponse(BaseModel):
    """机器人测试响应"""
    status: str
    message: str


@router.post("/baidu/test", response_model=BotTestResponse)
async def test_baidu_bot(slot: str = Query("0", alias="slot")):
    """测试百度机器人通知

    完全按照 baidu_webhook_test.py 的方式构建请求
    """
    try:
        # 加载配置
        config_path = get_config_path(slot)
        config = ConfigValidator.load_config(config_path)

        # 获取百度机器人配置
        baidu_config = config.get("bots", {}).get("baidu", {})

        if not baidu_config.get("enabled"):
            return BotTestResponse(
                status="error",
                message="百度机器人未启用"
            )

        api_url = baidu_config.get("api_url", "")
        access_token = baidu_config.get("access_token", "")
        group_id = baidu_config.get("group_id", "")

        if not api_url or not access_token or not group_id:
            return BotTestResponse(
                status="error",
                message="配置信息不完整，请检查 API 地址、Access Token 和群组 ID"
            )

        # 完全按照 baidu_webhook_test.py 的方式构建请求
        import requests

        # 构建 URL（与 baidu_webhook_test.py 完全一致）
        webhook_url = f"{api_url}?access_token={access_token}"

        # 构建 payload（与 baidu_webhook_test.py 完全一致）
        payload = {
            "message": {
                "header": {
                    "toid": [int(group_id)]
                },
                "body": [
                    {
                        "type": "TEXT",
                        "content": "🤖 测试消息\n\n这是来自 Bilibili Bot 的测试通知\n\n如果收到此消息，说明配置成功！"
                    }
                ]
            }
        }

        # 发送请求（与 baidu_webhook_test.py 完全一致）
        logger.info(f"[百度机器人测试] 发送测试消息到: {webhook_url}")
        logger.debug(f"[百度机器人测试] Payload: {payload}")

        response = requests.post(
            webhook_url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10
        )

        logger.info(f"[百度机器人测试] 响应状态码: {response.status_code}")
        logger.debug(f"[百度机器人测试] 响应内容: {response.text}")

        if response.status_code == 200:
            return BotTestResponse(
                status="ok",
                message="测试消息发送成功！请检查群组消息"
            )
        else:
            return BotTestResponse(
                status="error",
                message=f"发送失败: HTTP {response.status_code} - {response.text}"
            )

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        logger.error(f"[百度机器人测试] 请求失败: {error_msg}")

        # 特殊处理 502 错误
        if "502" in error_msg or "Bad Gateway" in error_msg:
            return BotTestResponse(
                status="error",
                message="发送失败: 502 Bad Gateway - 百度内部 API 需要在内网环境访问"
            )

        return BotTestResponse(
            status="error",
            message=f"发送失败: {error_msg}"
        )

    except Exception as e:
        logger.error(f"[百度机器人测试] 未知错误: {e}")
        return BotTestResponse(
            status="error",
            message=f"测试失败: {str(e)}"
        )
