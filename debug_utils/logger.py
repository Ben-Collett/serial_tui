import datetime
from pathlib import Path


LOG_FILE = Path("/tmp/serial_tui.log")


def log_debug(*args, **kwargs) -> None:
    timestamp = datetime.datetime.now().isoformat()
    parts = []
    for a in args:
        parts.append(str(a))
    for k, v in kwargs.items():
        parts.append(f"{k}={v}")
    msg = " ".join(parts) if parts else ""
    with LOG_FILE.open("a") as f:
        f.write(f"[{timestamp}] {msg}\n")
