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

import html as html_module
import logging
import os
import re
import smtplib
import urllib.parse
import urllib.request
from email.header import Header
from email.mime.multipart import MIMEMultipart
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


# --------------------------------------------------------------------- markdown

# 本仓库的推送正文都是自己生成的 markdown（日报 / 归因 / 调仓票），语法子集固定且可控：
# 标题、无序与有序列表、引用、表格、**粗体**、`代码`。Server酱会自己渲染，
# 但 SMTP 发纯文本时 Gmail 只会原样显示源码（表格尤其难读），故在此转成 HTML。
# 不引通用 markdown 依赖：输入不是任意用户内容，覆盖这个子集即可，且邮件必须内联样式
# ——Gmail 等客户端会剥掉 <style> 块。

_STYLE = {
    "body": "margin:0;padding:16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',"
    "'PingFang SC','Microsoft YaHei',sans-serif;font-size:15px;line-height:1.6;color:#1f2328;",
    "h1": "font-size:20px;margin:18px 0 10px;padding-bottom:6px;border-bottom:1px solid #d8dee4;",
    "h2": "font-size:17px;margin:16px 0 8px;",
    "h3": "font-size:15px;margin:14px 0 6px;",
    "p": "margin:8px 0;",
    "ul": "margin:8px 0;padding-left:22px;",
    "ol": "margin:8px 0;padding-left:22px;",
    "li": "margin:3px 0;",
    "quote": "margin:10px 0;padding:8px 12px;border-left:3px solid #d0d7de;background:#f6f8fa;color:#57606a;",
    "table": "border-collapse:collapse;margin:10px 0;width:100%;font-size:14px;",
    "th": "border:1px solid #d0d7de;padding:6px 10px;background:#f6f8fa;text-align:left;",
    "td": "border:1px solid #d0d7de;padding:6px 10px;",
    "code": "background:#f0f1f3;padding:1px 5px;border-radius:4px;font-family:Consolas,Monaco,monospace;font-size:90%;",
}

_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def _inline(text: str) -> str:
    """行内标记。先转义 HTML 再套标记——反过来会把生成的标签自己转义掉。"""
    out = html_module.escape(text, quote=False)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+?)`", rf'<code style="{_STYLE["code"]}">\1</code>', out)
    return out


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def markdown_to_html(text: str) -> str:
    """把本仓库生成的 markdown 转成内联样式的 HTML 邮件正文。"""
    lines = text.split("\n")
    out: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        # 表格：当前行以 | 开头且下一行是分隔行
        if stripped.startswith("|") and index + 1 < len(lines) and _TABLE_SEP.match(lines[index + 1]):
            header = _split_row(stripped)
            index += 2
            body: list[list[str]] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                body.append(_split_row(lines[index].strip()))
                index += 1
            cells = "".join(f'<th style="{_STYLE["th"]}">{_inline(c)}</th>' for c in header)
            rows = "".join(
                "<tr>" + "".join(f'<td style="{_STYLE["td"]}">{_inline(c)}</td>' for c in row) + "</tr>"
                for row in body
            )
            out.append(f'<table style="{_STYLE["table"]}"><thead><tr>{cells}</tr></thead><tbody>{rows}</tbody></table>')
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            level = min(len(heading.group(1)), 3)
            out.append(f'<h{level} style="{_STYLE[f"h{level}"]}">{_inline(heading.group(2))}</h{level}>')
            index += 1
            continue

        if stripped.startswith(">"):
            block = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                block.append(_inline(re.sub(r"^\s*>\s?", "", lines[index])))
                index += 1
            out.append(f'<div style="{_STYLE["quote"]}">{"<br>".join(block)}</div>')
            continue

        if re.match(r"^[-*]\s+", stripped):
            items = []
            while index < len(lines) and re.match(r"^[-*]\s+", lines[index].strip()):
                items.append(f'<li style="{_STYLE["li"]}">{_inline(re.sub(r"^[-*]\s+", "", lines[index].strip()))}</li>')
                index += 1
            out.append(f'<ul style="{_STYLE["ul"]}">{"".join(items)}</ul>')
            continue

        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while index < len(lines) and re.match(r"^\d+\.\s+", lines[index].strip()):
                items.append(f'<li style="{_STYLE["li"]}">{_inline(re.sub(r"^\d+\.\s+", "", lines[index].strip()))}</li>')
                index += 1
            out.append(f'<ol style="{_STYLE["ol"]}">{"".join(items)}</ol>')
            continue

        # 普通段落：连续非空且非块级起始的行合并
        para = []
        while index < len(lines):
            current = lines[index].strip()
            if not current or current.startswith(("#", ">", "|")) or re.match(r"^([-*]|\d+\.)\s+", current):
                break
            para.append(_inline(current))
            index += 1
        out.append(f'<p style="{_STYLE["p"]}">{"<br>".join(para)}</p>')

    return f'<html><body style="{_STYLE["body"]}">{"".join(out)}</body></html>'


# --------------------------------------------------------------------- 渠道


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
    # multipart/alternative：纯文本兜底 + HTML 正文。Gmail 等客户端优先取后者，
    # 不支持 HTML 的客户端仍能看到原 markdown（本身可读）。
    message = MIMEMultipart("alternative")
    message.attach(MIMEText(text, "plain", "utf-8"))
    message.attach(MIMEText(markdown_to_html(text), "html", "utf-8"))
    message["Subject"] = Header(title, "utf-8")
    message["From"] = username
    message["To"] = ", ".join(recipients)
    port = int(channel.get("port", 465))
    with smtplib.SMTP_SSL(host, port, timeout=15) as server:
        server.login(username, password)
        server.sendmail(username, recipients, message.as_string())
    return True
