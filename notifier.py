from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


def post_message(webhook_url: str | None, text: str, timeout: int = 10) -> bool:
    """Slack Incoming Webhook へ投稿する。成功すれば True。"""
    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL is not set; skipping Slack post")
        return False

    payload = {"text": text}
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
            if 200 <= status < 300:
                return True
            logger.error("Slack webhook returned status %s", status)
            return False
    except urllib.error.HTTPError as exc:
        logger.error("Slack webhook HTTP error: %s %s", exc.code, exc.reason)
    except urllib.error.URLError as exc:
        logger.error("Slack webhook connection error: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Slack webhook unexpected error: %s", exc)
    return False

