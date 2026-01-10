"""WeCom (企业微信) notification channel."""

import httpx

from llmtrigger.core.logging import get_logger
from llmtrigger.models.notification import NotificationTask
from llmtrigger.models.rule import NotifyTarget
from llmtrigger.notification.channels.base import NotificationChannel

logger = get_logger(__name__)

WECOM_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"


class WeComChannel(NotificationChannel):
    """WeCom (企业微信) webhook notification channel."""

    def __init__(self):
        """Initialize HTTP client."""
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def channel_type(self) -> str:
        return "wecom"

    async def send(self, target: NotifyTarget, task: NotificationTask) -> bool:
        """Send message via WeCom webhook.

        Args:
            target: Target with webhook_key
            task: Notification task

        Returns:
            True if sent successfully
        """
        if not target.webhook_key:
            logger.warning("WeCom target missing webhook_key")
            return False

        url = f"{WECOM_WEBHOOK_URL}?key={target.webhook_key}"

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": task.message,
            },
        }

        try:
            response = await self._client.post(url, json=payload)
            result = response.json()

            if result.get("errcode") == 0:
                logger.info("WeCom message sent", task_id=task.task_id)
                return True
            else:
                logger.warning(
                    "WeCom send failed",
                    errcode=result.get("errcode"),
                    errmsg=result.get("errmsg"),
                )
                return False

        except Exception as e:
            logger.error("WeCom send error", error=str(e))
            return False

    async def close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()
