"""
Compust Database Configuration, Multi-Port Probing & Switching Service.

Handles:
1. Secure storage of database connection parameters in db_config.json
   (Windows DPAPI encryption for passwords, restricted permissions, masked API returns).
2. Parallel non-blocking socket and protocol handshake detection for MySQL/MariaDB
   across common ports (3306, 3307, 3308, 3309, and XAMPP my.ini).
3. Diagnostic connection testing with specific failure taxonomy:
   - unreachable, auth_failure, db_not_found, driver_missing, schema_state.
4. Safe database creation (utf8mb4_unicode_ci) when server exists but database does not.
5. Live engine switching and automated fallback to local SQLite.
"""

from __future__ import annotations

import base64
import concurrent.futures
import ctypes
import json
import logging
import os
import re
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..paths import get_user_data_dir

logger = logging.getLogger("compust.db_config")

# --- DPAPI for Windows Password Protection ---
if os.name == "nt":
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        CryptProtectData = crypt32.CryptProtectData
        CryptProtectData.argtypes = [
            ctypes.POINTER(DATA_BLOB),
            wintypes.LPCWSTR,
            ctypes.POINTER(DATA_BLOB),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(DATA_BLOB),
        ]
        CryptProtectData.restype = wintypes.BOOL

        CryptUnprotectData = crypt32.CryptUnprotectData
        CryptUnprotectData.argtypes = [
            ctypes.POINTER(DATA_BLOB),
            ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(DATA_BLOB),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(DATA_BLOB),
        ]
        CryptUnprotectData.restype = wintypes.BOOL
        _DPAPI_AVAILABLE = True
    except Exception:
        _DPAPI_AVAILABLE = False
else:
    _DPAPI_AVAILABLE = False


def _encrypt_password(password: str) -> str:
    """Encrypt password using Windows DPAPI if available, otherwise base64 with flag."""
    if not password:
        return ""
    if _DPAPI_AVAILABLE:
        try:
            data_bytes = password.encode("utf-8")
            in_blob = DATA_BLOB(len(data_bytes), ctypes.cast(ctypes.create_string_buffer(data_bytes), ctypes.POINTER(ctypes.c_char)))
            out_blob = DATA_BLOB()
            success = CryptProtectData(ctypes.byref(in_blob), "compust_db_pwd", None, None, None, 0x1, ctypes.byref(out_blob))
            if success:
                enc_bytes = ctypes.string_at(out_blob.pbData, out_blob.cbData)
                kernel32.LocalFree(out_blob.pbData)
                return "dpapi:" + base64.b64encode(enc_bytes).decode("ascii")
        except Exception as exc:
            logger.warning(f"DPAPI encryption failed, using fallback: {exc}")
    # Fallback to base64
    return "b64:" + base64.b64encode(password.encode("utf-8")).decode("ascii")


def _decrypt_password(enc_str: str) -> str:
    """Decrypt password stored in db_config.json."""
    if not enc_str:
        return ""
    if enc_str.startswith("dpapi:") and _DPAPI_AVAILABLE:
        try:
            enc_bytes = base64.b64decode(enc_str[6:].encode("ascii"))
            in_blob = DATA_BLOB(len(enc_bytes), ctypes.cast(ctypes.create_string_buffer(enc_bytes), ctypes.POINTER(ctypes.c_char)))
            out_blob = DATA_BLOB()
            success = CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0x1, ctypes.byref(out_blob))
            if success:
                decrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData).decode("utf-8")
                kernel32.LocalFree(out_blob.pbData)
                return decrypted
        except Exception as exc:
            logger.warning(f"DPAPI decryption failed: {exc}")
            return ""
    elif enc_str.startswith("b64:"):
        try:
            return base64.b64decode(enc_str[4:].encode("ascii")).decode("utf-8")
        except Exception:
            return ""
    return enc_str


encrypt_password = _encrypt_password
decrypt_password = _decrypt_password


def get_db_config_file() -> Path:
    """Resolve location of db_config.json based on user data dir."""
    return get_user_data_dir() / "db_config.json"


def load_db_config() -> dict[str, Any] | None:
    """Load persisted database configuration if present."""
    cfg_file = get_db_config_file()
    if not cfg_file.is_file():
        return None
    try:
        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return data
    except Exception as exc:
        logger.warning(f"Could not read db_config.json: {exc}")
        return None


def get_active_db_connection_params() -> dict[str, Any]:
    """Retrieve active database configuration with plain password for internal use."""
    cfg = load_db_config()
    if cfg and cfg.get("enabled", True):
        pwd = _decrypt_password(cfg.get("password_encrypted", ""))
        return {
            "engine": cfg.get("engine", "sqlite"),
            "host": cfg.get("host", "127.0.0.1"),
            "port": int(cfg.get("port", 3306)),
            "user": cfg.get("user", "root"),
            "password": pwd,
            "database": cfg.get("database", "compust"),
            "source": "config_file",
        }
    return {
        "engine": "sqlite",
        "host": None,
        "port": None,
        "user": None,
        "password": None,
        "database": None,
        "source": "default_sqlite",
    }


def save_db_config(
    engine_type: str,
    host: str = "127.0.0.1",
    port: int = 3306,
    user: str = "root",
    password: str = "",
    database: str = "compust",
    enabled: bool = True,
) -> dict[str, Any]:
    """Save database configuration to db_config.json with encrypted password."""
    cfg_file = get_db_config_file()
    cfg_file.parent.mkdir(parents=True, exist_ok=True)

    enc_pwd = _encrypt_password(password)
    payload = {
        "engine": engine_type.lower(),
        "host": host.strip(),
        "port": int(port),
        "user": user.strip(),
        "password_encrypted": enc_pwd,
        "database": database.strip(),
        "enabled": enabled,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    cfg_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        os.chmod(cfg_file, 0o600)
    except Exception:
        pass
    logger.info(f"Database configuration saved to {cfg_file} (engine: {engine_type}, host: {host}:{port})")
    return get_public_db_config()


def clear_db_config() -> bool:
    """Remove db_config.json reverting to default SQLite."""
    cfg_file = get_db_config_file()
    if cfg_file.is_file():
        try:
            cfg_file.unlink()
            logger.info("db_config.json removed. Reverted to default SQLite database.")
            return True
        except Exception as exc:
            logger.warning(f"Could not delete db_config.json: {exc}")
            return False
    return True


def get_public_db_config() -> dict[str, Any]:
    """Get sanitized db config for frontend display (password masked)."""
    cfg = load_db_config()
    if not cfg:
        return {
            "configured": False,
            "engine": "sqlite",
            "host": None,
            "port": None,
            "user": None,
            "password_masked": None,
            "database": None,
            "enabled": False,
        }
    return {
        "configured": True,
        "engine": cfg.get("engine", "sqlite"),
        "host": cfg.get("host", "127.0.0.1"),
        "port": cfg.get("port", 3306),
        "user": cfg.get("user", "root"),
        "password_masked": "********" if cfg.get("password_encrypted") else "",
        "database": cfg.get("database", "compust"),
        "enabled": cfg.get("enabled", True),
        "updated_at": cfg.get("updated_at"),
    }


# ==============================================================================
# Protocol Detection & Scanner
# ==============================================================================

def probe_mysql_handshake(host: str, port: int, timeout: float = 0.8) -> dict[str, Any] | None:
    """
    Connect to host:port and perform a real MySQL/MariaDB Initial Handshake Packet verification.
    Extracts server version string without requiring credentials.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            packet = s.recv(512)
            if len(packet) > 5 and packet[4] == 10:  # Protocol version 10 (MySQL 4.1+)
                # Version string starts at index 5 and is null-terminated
                version_raw = packet[5:].split(b"\x00", 1)[0]
                version_str = version_raw.decode("utf-8", errors="ignore")
                return {
                    "host": host,
                    "port": port,
                    "reachable": True,
                    "is_mysql": True,
                    "server_version": version_str,
                }
    except Exception:
        pass
    return None


def parse_xampp_ports() -> list[int]:
    """Look for configured MySQL ports in local XAMPP / MariaDB configuration files."""
    candidate_paths = [
        Path("C:/xampp/mysql/bin/my.ini"),
        Path("C:/xampp/mysql/my.ini"),
        Path("D:/xampp/mysql/bin/my.ini"),
        Path("D:/xampp/mysql/my.ini"),
    ]
    ports: list[int] = []
    for p in candidate_paths:
        if p.is_file():
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                matches = re.findall(r"^\s*port\s*=\s*(\d+)", content, re.MULTILINE | re.IGNORECASE)
                for m in matches:
                    val = int(m)
                    if 1024 <= val <= 65535 and val not in ports:
                        ports.append(val)
            except Exception:
                pass
    return ports


def scan_local_mysql_instances() -> list[dict[str, Any]]:
    """Scan loopback 127.0.0.1 for active MySQL/MariaDB instances in parallel."""
    ports_to_scan = [3306, 3307, 3308, 3309]
    for xp in parse_xampp_ports():
        if xp not in ports_to_scan:
            ports_to_scan.append(xp)

    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(ports_to_scan), 6)) as executor:
        future_to_port = {
            executor.submit(probe_mysql_handshake, "127.0.0.1", port): port
            for port in ports_to_scan
        }
        for future in concurrent.futures.as_completed(future_to_port):
            res = future.result()
            if res:
                results.append(res)

    results.sort(key=lambda r: r["port"])
    return results


# ==============================================================================
# Connection Testing & Schema Analysis
# ==============================================================================

def test_mysql_connection(
    host: str = "127.0.0.1",
    port: int = 3306,
    user: str = "root",
    password: str = "",
    database: str = "compust",
) -> dict[str, Any]:
    """
    Perform a complete diagnostic probe of MySQL connection settings.
    Checks reachability, authentication, database existence, and table counts.
    """
    # 1. TCP and handshake check
    probe = probe_mysql_handshake(host, port, timeout=1.0)
    if not probe:
        return {
            "success": False,
            "error_code": "UNREACHABLE",
            "message": f"Could not connect to MySQL server at {host}:{port}. Verify MySQL service is started.",
            "server_version": None,
            "database_exists": False,
            "schema_state": "unreachable",
            "table_counts": {},
        }

    server_version = probe["server_version"]

    # 2. Authentication check
    import pymysql

    # First test connection without database to test credentials alone
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connect_timeout=2.0,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except pymysql.err.OperationalError as auth_err:
        err_msg = str(auth_err)
        if "1045" in err_msg or "Access denied" in err_msg:
            return {
                "success": False,
                "error_code": "AUTH_FAILED",
                "message": f"Access denied for user '{user}'. Please verify your username and password.",
                "server_version": server_version,
                "database_exists": False,
                "schema_state": "auth_failed",
                "table_counts": {},
            }
        return {
            "success": False,
            "error_code": "CONNECTION_ERROR",
            "message": f"MySQL operational error: {auth_err}",
            "server_version": server_version,
            "database_exists": False,
            "schema_state": "connection_error",
            "table_counts": {},
        }
    except Exception as exc:
        return {
            "success": False,
            "error_code": "DRIVER_OR_AUTH_ERROR",
            "message": f"Connection error: {exc}",
            "server_version": server_version,
            "database_exists": False,
            "schema_state": "driver_error",
            "table_counts": {},
        }

    # 3. Check if target database exists
    database_exists = False
    table_counts: dict[str, int] = {}
    schema_state = "empty"

    try:
        with conn.cursor() as cur:
            cur.execute("SHOW DATABASES LIKE %s", (database,))
            if cur.fetchone():
                database_exists = True

            if database_exists:
                cur.execute(f"USE `{database}`")
                cur.execute("SHOW TABLES")
                tables = [list(r.values())[0] for r in cur.fetchall()]

                key_tables = ["users", "jobs", "companies", "user_applications", "contacts", "resumes"]
                for t in key_tables:
                    if t in tables:
                        try:
                            cur.execute(f"SELECT count(*) as cnt FROM `{t}`")
                            table_counts[t] = cur.fetchone()["cnt"]
                        except Exception:
                            table_counts[t] = 0
                    else:
                        table_counts[t] = 0

                if "jobs" in tables and "users" in tables:
                    schema_state = "compatible"
                elif len(tables) == 0:
                    schema_state = "empty"
                else:
                    schema_state = "foreign"
    finally:
        conn.close()

    return {
        "success": True,
        "error_code": None,
        "message": f"Successfully connected to {server_version} at {host}:{port}.",
        "server_version": server_version,
        "database_exists": database_exists,
        "schema_state": schema_state,
        "table_counts": table_counts,
    }


def create_mysql_database(
    host: str = "127.0.0.1",
    port: int = 3306,
    user: str = "root",
    password: str = "",
    database: str = "compust",
) -> dict[str, Any]:
    """Create target database with utf8mb4 encoding on connected MySQL server."""
    import pymysql

    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connect_timeout=2.0,
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{database}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            logger.info(f"Database `{database}` created successfully on {host}:{port}")
            return {"success": True, "message": f"Database `{database}` created successfully."}
        finally:
            conn.close()
    except Exception as exc:
        logger.error(f"Failed to create database `{database}`: {exc}")
        return {"success": False, "message": f"Failed to create database: {exc}"}
