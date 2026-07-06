"""Permanent local server for the weather forecast app."""

from __future__ import annotations

import socket
import sys
import webbrowser
from pathlib import Path

from waitress import serve

from app import app

HOST = "127.0.0.1"
PORT = 5050
URL = f"http://{HOST}:{PORT}"


def port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def server_already_running() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((HOST, PORT)) == 0


def main() -> None:
    if server_already_running():
        print(f"Weather app is already running at {URL}")
        if "--open" in sys.argv:
            webbrowser.open(URL)
        return

    if not port_is_available(HOST, PORT):
        print(f"Port {PORT} is already in use. Close the other app and try again.")
        sys.exit(1)

    print(f"Starting weather server at {URL}")
    print("Press Ctrl+C to stop.")

    if "--open" in sys.argv:
        webbrowser.open(URL)

    serve(app, host=HOST, port=PORT, threads=4)


if __name__ == "__main__":
    main()
