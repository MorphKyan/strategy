import subprocess
import sys
from pathlib import Path


def test_repeated_monthly_report_preserves_original_file(tmp_path):
    live = tmp_path / "live/account"
    shadow = tmp_path / "sim/model/runs/first"
    live.mkdir(parents=True)
    shadow.mkdir(parents=True)
    data = "date,total_value,cash\n2024-06-03,1000,100\n2024-06-04,1000,100\n"
    (live / "real_nav.csv").write_text(data)
    (shadow / "nav.csv").write_text(data)
    reports = tmp_path / "reports"
    command = [sys.executable, str(Path(__file__).parents[1] / "scripts/report_live_attribution.py"),
               "--live-id", "account", "--shadow-id", "model", "--month", "2024-06",
               "--live-root", str(tmp_path / "live"), "--sim-root", str(tmp_path / "sim"),
               "--report-root", str(reports)]
    subprocess.run(command, capture_output=True, text=True, check=True)
    path = reports / "2024-06_account_attribution.md"
    before = path.read_bytes()
    second = subprocess.run(command, capture_output=True, text=True, check=False)
    assert second.returncode != 0 and "FileExistsError" in second.stderr
    assert path.read_bytes() == before
