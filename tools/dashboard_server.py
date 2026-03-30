"""Start the BoxBunny dashboard server and write the URL file."""
import logging
import socket
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

WS = Path(__file__).resolve().parents[1]
URL_FILE = "/tmp/boxbunny_dashboard_url.txt"

# Ensure dashboard package is importable
for p in [WS / "src" / "boxbunny_dashboard", WS / "src" / "boxbunny_core"]:
    path_str = str(p)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def main() -> None:
    import uvicorn
    from boxbunny_dashboard.server import create_app

    ip = _get_local_ip()
    url = f"http://{ip}:8080"

    try:
        with open(URL_FILE, "w") as f:
            f.write(url)
    except OSError as exc:
        logger.warning("Could not write URL file: %s", exc)

    logger.info("Dashboard: %s", url)
    uvicorn.run(create_app(), host="0.0.0.0", port=8080, log_level="warning")


if __name__ == "__main__":
    main()
