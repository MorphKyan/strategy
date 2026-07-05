from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    platform_dir = Path(__file__).resolve().parents[1]
    app_path = platform_dir / "src" / "platform_dashboard" / "app.py"
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        os.environ.get("PORT", "8501"),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    return subprocess.call(command, cwd=platform_dir)


if __name__ == "__main__":
    raise SystemExit(main())
