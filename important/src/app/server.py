"""
Compust Dedicated Server Runner.

Provides loopback-only (127.0.0.1) socket binding with exclusive access
(SO_EXCLUSIVEADDRUSE on Windows) to prevent silent duplicate port hijacking,
and passes the pre-bound exclusive socket directly to Uvicorn.
"""

import argparse
import logging
import os
import socket
import sys
from pathlib import Path

import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("compust.server")


def create_exclusive_loopback_socket(host: str, port: int, backlog: int = 128) -> socket.socket:
    """
    Create a TCP listening socket bound strictly to host:port with SO_EXCLUSIVEADDRUSE on Windows.
    This guarantees that on Windows, no second process can silently hijack or share the port.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        except Exception as exc:
            logger.warning(f"Could not set SO_EXCLUSIVEADDRUSE: {exc}")

    try:
        sock.bind((host, port))
        sock.listen(backlog)
        sock.set_inheritable(True)
        return sock
    except OSError as err:
        sock.close()
        raise err


def run_server():
    parser = argparse.ArgumentParser(description="Compust Uvicorn Server with Exclusive Binding")
    parser.add_argument("--host", default="127.0.0.1", help="Binding host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--mode", default=None, choices=["installed", "dev"], help="Runtime mode")
    parser.add_argument("--reload", action="store_true", help="Enable reload (dev only)")
    parser.add_argument("--log-level", default="info", help="Uvicorn log level")

    args = parser.parse_args()

    # Enforce loopback binding safety
    if args.host not in ("127.0.0.1", "localhost"):
        logger.warning(f"Non-loopback host '{args.host}' requested. Forcing loopback '127.0.0.1' for security.")
        args.host = "127.0.0.1"

    if args.mode:
        os.environ["COMPUST_APP_MODE"] = args.mode

    os.environ["COMPUST_ACTIVE_PORT"] = str(args.port)

    logger.info(f"Binding exclusive socket on {args.host}:{args.port}...")
    try:
        exclusive_sock = create_exclusive_loopback_socket(args.host, args.port)
    except OSError as exc:
        logger.error(f"Failed to bind exclusively on {args.host}:{args.port}: {exc}")
        sys.exit(1)

    # Initialize Uvicorn with pre-bound socket
    config = uvicorn.Config(
        "src.app.main:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level.lower(),
        access_log=False,
    )
    server = uvicorn.Server(config)

    logger.info(f"Compust backend server starting on http://{args.host}:{args.port} (mode: {os.environ.get('COMPUST_APP_MODE', 'dev')})")
    try:
        server.run(sockets=[exclusive_sock])
    finally:
        try:
            exclusive_sock.close()
        except Exception:
            pass


if __name__ == "__main__":
    run_server()
