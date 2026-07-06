"""调仓提醒推送（蓝图主线 A3）。

设计约束：
- `send_notification()` **永不抛异常中断主流程**——票已落盘，推送失败无非手动去看，
  失败只打日志并返回 False。
- 密钥一律走环境变量，配置文件里只写渠道与非敏感参数，密钥不入库不入 git。

渠道配置有两种方式，二选一：

1. **零配置（推荐）**：只设环境变量，运行时自动发现渠道——
   - Server酱：设 `RQ_SERVERCHAN_KEY`（sct.ftqq.com 申请的 SendKey）
   - SMTP 邮件：设 `RQ_SMTP_HOST` / `RQ_SMTP_USERNAME` / `RQ_SMTP_PASSWORD` / `RQ_SMTP_TO`
     （可选 `RQ_SMTP_PORT`，默认 465 SSL）
2. **显式配置**：在平台 YAML 里加可选的 `notify.channels` 块（存在时优先于自动发现）：

   notify:
     channels:
       - type: serverchan
         key_env: RQ_SERVERCHAN_KEY          # 可省略，默认即此
       - type: smtp
         host: smtp.example.com
         port: 465
         username: me@example.com
         password_env: RQ_SMTP_PASSWORD      # 可省略，默认即此
         to: [me@example.com]
"""

from __future__ import annotations

import logging
import os
import smtplib
import urllib.parse
import urllib.request
from email.header import Header
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)

SERVERCHAN_KEY_ENV = "RQ_SERVERCHAN_KEY"
SMTP_HOST_ENV = "RQ_SMTP_HOST"
SMTP_PORT_ENV = "RQ_SMTP_PORT"
SMTP_USERNAME_ENV = "RQ_SMTP_USERNAME"
SMTP_PASSWORD_ENV = "RQ_SMTP_PASSWORD"
SMTP_TO_ENV = "RQ_SMTP_TO"


def resolve_channels(notify_config: dict[str, Any] | None) -> list[dict[str, Any]]:
    """显式 `notify.channels` 优先；否则按环境变量自动发现。"""
    explicit = (notify_config or {}).get("channels")
    if explicit:
        return list(explicit)
    channels: list[dict[str, Any]] = []
    if os.environ.get(SERVERCHAN_KEY_ENV):
        channels.append({"type": "serverchan"})
    if os.environ.get(SMTP_HOST_ENV) and os.environ.get(SMTP_USERNAME_ENV) and os.environ.get(SMTP_TO_ENV):
        channels.append(
            {
                "type": "smtp",
                "host": os.environ[SMTP_HOST_ENV],
                "port": int(os.environ.get(SMTP_PORT_ENV, "465")),
                "username": os.environ[SMTP_USERNAME_ENV],
                "to": [addr.strip() for addr in os.environ[SMTP_TO_ENV].split(",") if addr.strip()],
            }
        )
    return channels


def send_notification(title: str, text: str, notify_config: dict[str, Any] | None = None) -> bool:
    """向所有已配置渠道推送；任一渠道成功即返回 True。失败打日志，绝不抛异常。"""
    channels = resolve_channels(notify_config)
    if not channels:
        logger.warning("未配置任何通知渠道（设 %s 或 RQ_SMTP_* 环境变量，或在配置里写 notify.channels）", SERVERCHAN_KEY_ENV)
        return False
    ok_any = False
    for channel in channels:
        channel_type = str(channel.get("type", "")).lower()
        try:
            if channel_type == "serverchan":
                ok = _send_serverchan(channel, title, text)
            elif channel_type == "smtp":
                ok = _send_smtp(channel, title, text)
            else:
                logger.warning("未知通知渠道类型: %r", channel_type)
                ok = False
        except Exception:  # noqa: BLE001 - 推送失败不允许影响主流程
            logger.exception("通知渠道 %s 推送失败", channel_type)
            ok = False
        ok_any = ok_any or ok
    return ok_any


def _send_serverchan(channel: dict[str, Any], title: str, text: str) -> bool:
    key = os.environ.get(str(channel.get("key_env", SERVERCHAN_KEY_ENV)), "")
    if not key:
        logger.warning("Server酱 SendKey 未设置（环境变量 %s）", channel.get("key_env", SERVERCHAN_KEY_ENV))
        return False
    url = f"https://sctapi.ftqq.com/{key}.send"
    payload = urllib.parse.urlencode({"title": title[:32], "desp": text}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(request, timeout=10) as response:
        ok = 200 <= response.status < 300
    if not ok:
        logger.warning("Server酱返回非 2xx 状态")
    return ok


def _send_smtp(channel: dict[str, Any], title: str, text: str) -> bool:
    host = channel.get("host", "")
    username = channel.get("username", "")
    recipients = list(channel.get("to") or [])
    password = os.environ.get(str(channel.get("password_env", SMTP_PASSWORD_ENV)), "")
    if not host or not username or not recipients:
        logger.warning("SMTP 渠道缺少 host/username/to 配置")
        return False
    if not password:
        logger.warning("SMTP 密码未设置（环境变量 %s）", channel.get("password_env", SMTP_PASSWORD_ENV))
        return False
    message = MIMEText(text, "plain", "utf-8")
    message["Subject"] = Header(title, "utf-8")
    message["From"] = username
    message["To"] = ", ".join(recipients)
    port = int(channel.get("port", 465))
    with smtplib.SMTP_SSL(host, port, timeout=15) as server:
        server.login(username, password)
        server.sendmail(username, recipients, message.as_string())
    return True
