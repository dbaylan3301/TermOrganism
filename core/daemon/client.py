from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any


def client_send(file_path: str, context: dict[str, Any] | None = None, mode: str = "auto", socket_path: str = "/tmp/termorganism.sock") -> dict[str, Any]:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(5.0)

    try:
        sock.connect(socket_path)

        request = {
            "file_path": file_path,
            "context": context or {},
            "mode": mode,
        }

        sock.sendall(json.dumps(request).encode("utf-8"))
        sock.shutdown(socket.SHUT_WR)

        response = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            response += chunk

        if not response:
            return {
                "success": False,
                "error": "empty daemon response",
                "mode": "daemon_client",
            }

        return json.loads(response.decode("utf-8"))
    finally:
        sock.close()
