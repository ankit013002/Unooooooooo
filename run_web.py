"""Run the complete UNO web app on this laptop."""

from __future__ import annotations

import os
import socket

import uvicorn


def local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            connection.connect(("8.8.8.8", 80))
            return connection.getsockname()[0]
    except OSError:
        return "localhost"


if __name__ == "__main__":
    host = os.getenv("UNO_WEB_HOST", "0.0.0.0")
    port = int(os.getenv("UNO_WEB_PORT", "8000"))
    print(f"UNO is available on this laptop: http://localhost:{port}")
    print(f"Share this address on the same network: http://{local_ip()}:{port}")
    uvicorn.run("Web.app:app", host=host, port=port, reload=False)
