"""每日实盘自动化调度器：在容器内按北京时间工作日定时触发 run_live_cycle.py cycle。"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def parse_run_time(value: str) -> tuple[int, int]:
    """解析 HH:MM 格式的 24 小时触发时间。"""
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"无效触发时间格式（需 HH:MM）: {value!r}")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"触发时间超出范围: {value!r}")
    return hour, minute


def next_run_datetime(
    now: datetime,
    hour: int,
    minute: int,
    weekdays: set[int] | None = None,
) -> datetime:
    """计算不早于当前时刻的下一个目标工作日触发时间（严格晚于 now）。"""
    allowed = {0, 1, 2, 3, 4} if weekdays is None else set(weekdays)
    if not allowed or not allowed.issubset({0, 1, 2, 3, 4, 5, 6}):
        raise ValueError(f"无效星期集合: {allowed!r}")
    for offset in range(8):
        candidate_date = now.date() + timedelta(days=offset)
        if candidate_date.weekday() not in allowed:
            continue
        candidate = datetime.combine(candidate_date, time(hour, minute), tzinfo=now.tzinfo)
        if candidate > now:
            return candidate
    raise RuntimeError("未能在 7 天内找到下一个运行日")


def build_cycle_command(
    config: str,
    portfolio: str,
    *,
    sync: bool = True,
    notify: bool = True,
    shadow: str | None = None,
    asof_date: str | None = None,
) -> list[str]:
    """构造 run_live_cycle.py cycle 调用命令。"""
    script = ROOT / "scripts" / "run_live_cycle.py"
    command = [
        sys.executable,
        "-u",
        str(script),
        "cycle",
        "--config",
        config,
        "--portfolio",
        portfolio,
    ]
    if asof_date:
        command.extend(["--asof-date", asof_date])
    if sync:
        command.append("--sync")
    if notify:
        command.append("--notify")
    if shadow:
        command.extend(["--shadow", shadow])
    return command


def execute_with_retries(
    command: list[str],
    *,
    max_retries: int = 2,
    retry_delay_seconds: float = 120.0,
    stop_event: threading.Event | None = None,
    runner=subprocess.run,
) -> int:
    """执行单次环路；非零退出码时按间隔重试，支持中断等待。"""
    attempts = max(1, max_retries + 1)
    for attempt in range(1, attempts + 1):
        ts = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] 开始执行实盘环路（第 {attempt}/{attempts} 次）: {' '.join(command)}", flush=True)
        result = runner(command, cwd=ROOT)
        code = int(result.returncode)
        ts_end = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts_end}] 执行结束，退出码: {code}", flush=True)
        if code == 0:
            return 0
        if attempt < attempts:
            print(f"[{ts_end}] 等待 {retry_delay_seconds:.0f}s 后重试...", flush=True)
            if stop_event is not None:
                if stop_event.wait(retry_delay_seconds):
                    return code
            else:
                threading.Event().wait(retry_delay_seconds)
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily live-portfolio scheduler for Docker/Unraid worker.")
    parser.add_argument("--config", default=os.environ.get("LIVE_CONFIG", ""), help="Platform YAML config path.")
    parser.add_argument("--portfolio", default=os.environ.get("LIVE_PORTFOLIO", ""), help="Live portfolio id.")
    parser.add_argument("--time", default=os.environ.get("LIVE_RUN_TIME", "18:15"), help="Daily trigger time HH:MM (Asia/Shanghai).")
    parser.add_argument("--shadow", default=os.environ.get("LIVE_SHADOW_PORTFOLIO", "") or None, help="Optional shadow sim portfolio id.")
    parser.add_argument("--no-sync", action="store_true", help="Disable --sync.")
    parser.add_argument("--no-notify", action="store_true", help="Disable --notify.")
    parser.add_argument("--max-retries", type=int, default=int(os.environ.get("LIVE_MAX_RETRIES", "2")), help="Retry attempts on failure.")
    parser.add_argument(
        "--retry-delay-seconds",
        type=float,
        default=float(os.environ.get("LIVE_RETRY_DELAY_SECONDS", "120")),
        help="Seconds to wait before retry.",
    )
    parser.add_argument("--asof-date", default=None, help="Optional as-of date (for --run-once).")
    parser.add_argument("--run-once", action="store_true", help="Run immediately once and exit.")
    args = parser.parse_args()

    if not args.config or not args.portfolio:
        parser.error("必须通过 --config/--portfolio 或 LIVE_CONFIG/LIVE_PORTFOLIO 指定配置与组合 ID。")

    hour, minute = parse_run_time(args.time)
    sync = _env_flag("LIVE_SYNC", True) and not args.no_sync
    notify = _env_flag("LIVE_NOTIFY", True) and not args.no_notify

    stop_event = threading.Event()

    def _handle_signal(signum: int, _frame: object) -> None:
        print(f"收到退出信号 {signum}，准备停止调度器...", flush=True)
        stop_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    if args.run_once:
        cmd = build_cycle_command(
            args.config,
            args.portfolio,
            sync=sync,
            notify=notify,
            shadow=args.shadow,
            asof_date=args.asof_date,
        )
        return execute_with_retries(
            cmd,
            max_retries=args.max_retries,
            retry_delay_seconds=args.retry_delay_seconds,
            stop_event=stop_event,
        )

    print(
        f"实盘调度器已启动 | 组合={args.portfolio} | 配置={args.config} | "
        f"工作日触发={hour:02d}:{minute:02d} (Asia/Shanghai) | sync={sync} | notify={notify}",
        flush=True,
    )
    while not stop_event.is_set():
        now = datetime.now(BEIJING_TZ)
        target = next_run_datetime(now, hour, minute)
        wait_seconds = max(0.0, (target - now).total_seconds())
        print(f"下次运行时间: {target.strftime('%Y-%m-%d %H:%M:%S %Z')}（约 {wait_seconds / 3600:.2f} 小时后）", flush=True)
        if stop_event.wait(wait_seconds):
            break
        cmd = build_cycle_command(
            args.config,
            args.portfolio,
            sync=sync,
            notify=notify,
            shadow=args.shadow,
        )
        execute_with_retries(
            cmd,
            max_retries=args.max_retries,
            retry_delay_seconds=args.retry_delay_seconds,
            stop_event=stop_event,
        )
    print("调度器已退出。", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
