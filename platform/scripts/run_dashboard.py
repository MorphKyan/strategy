from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    platform_dir = Path(__file__).resolve().parents[1]
    if not (platform_dir / "dashboard_web" / "dist" / "index.html").is_file():
        print("请先执行 pnpm -C platform/dashboard_web build。", file=sys.stderr)
        return 1
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.platform_dashboard.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        os.environ.get("PORT", "8501"),
    ]
    return subprocess.call(command, cwd=platform_dir)


if __name__ == "__main__":
    raise SystemExit(main())
