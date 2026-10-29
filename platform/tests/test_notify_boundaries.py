import subprocess
import sys
from pathlib import Path

from src.platform_core import notify


def test_malformed_markdown_always_advances_parser():
    text = "#\n#hashtag\n| orphan |\n####### not a heading\n<script>\n"
    result = subprocess.run(
        [sys.executable, "-c", "import sys; from src.platform_core.notify import markdown_to_html; print(markdown_to_html(sys.stdin.read()))"],
        cwd=Path(__file__).parents[1], input=text, capture_output=True, text=True, timeout=3, check=True,
    )
    assert "#hashtag" in result.stdout and "| orphan |" in result.stdout
    assert "&lt;script&gt;" in result.stdout


def test_explicit_empty_channels_disable_environment_autodiscovery(monkeypatch):
    monkeypatch.setenv("RQ_SERVERCHAN_KEY", "SCT_test")
    assert notify.resolve_channels({"channels": []}) == []
    assert not notify.send_notification("title", "text", {"channels": []})


def test_invalid_environment_port_does_not_interrupt_main_flow(monkeypatch):
    for key in ("RQ_SMTP_HOST", "RQ_SMTP_USERNAME", "RQ_SMTP_TO"):
        monkeypatch.setenv(key, "configured")
    monkeypatch.setenv("RQ_SMTP_PORT", "invalid-port")
    assert not notify.send_notification("title", "text")


def test_notification_errors_do_not_log_secret_request_url(monkeypatch, caplog):
    secret = "SCT_test_sensitive"
    monkeypatch.setenv("RQ_SERVERCHAN_KEY", secret)

    def fail(request, timeout):
        raise OSError(request.full_url)

    monkeypatch.setattr(notify.urllib.request, "urlopen", fail)
    assert not notify.send_notification("title", "text", {"channels": [{"type": "serverchan"}]})
    assert "OSError" in caplog.text
    assert secret not in caplog.text and "sctapi.ftqq.com" not in caplog.text
