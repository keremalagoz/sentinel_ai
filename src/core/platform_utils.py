"""Platform Utilities

Merkezi platform tespit ve yardimci fonksiyonlari.
Tum tool'lar ve core moduller bu modulu kullanir.

Sprint 3.6 Track B7: Linux platform uyumlulugu icin temel modul.
"""

import os
import platform
import subprocess
import sys
import tempfile
from typing import Optional


_PLATFORM: str = platform.system()  # 'Linux', 'Windows', 'Darwin'


def is_linux() -> bool:
    """Isletim sistemi Linux mu?"""
    return _PLATFORM == "Linux"


def is_windows() -> bool:
    """Isletim sistemi Windows mu?"""
    return _PLATFORM == "Windows"


def is_macos() -> bool:
    """Isletim sistemi macOS mu?"""
    return _PLATFORM == "Darwin"


def get_shell() -> str:
    """Platform icin varsayilan shell donurur."""
    if is_windows():
        return "powershell.exe"
    return "/bin/bash"


def get_shell_exec_flag() -> str:
    """Shell'in komut calistirma parametresini dondurur."""
    if is_windows():
        return "-Command"
    return "-c"


def get_ping_count_flag() -> str:
    """Ping icin paket sayisi parametresini dondurur.

    Windows: ``-n``
    Linux/macOS: ``-c``
    """
    if is_windows():
        return "-n"
    return "-c"


def get_temp_dir() -> str:
    """Platform icin guvenli gecici dizin dondurur.

    Linux/macOS: ``/tmp``
    Windows: ``%TEMP%\\sentinel`` (olusturulur)
    """
    if is_windows():
        base = os.path.join(
            os.environ.get("TEMP", tempfile.gettempdir()), "sentinel"
        )
        os.makedirs(base, exist_ok=True)
        return base
    return tempfile.gettempdir()


def get_console_encoding() -> str:
    """Isletim sistemi konsol karakter kodlamasini dondurur.

    Linux/macOS: ``utf-8``
    Windows: OEM code page (orn: ``cp857`` Turkce)
    """
    if is_windows():
        try:
            result = subprocess.run(
                ["chcp"],
                capture_output=True,
                text=True,
                shell=True,
            )
            cp = result.stdout.strip().split(":")[-1].strip()
            return f"cp{cp}"
        except Exception:
            return "cp1254"  # Turkish Windows fallback
    return "utf-8"


def pipe_echo_cmd(payload: str) -> str:
    """``echo | <payload>`` kalibini platform-uyumlu olusturur.

    Windows: ``cmd.exe /c "echo | <payload>"``  (list olarak build_command icinde)
    Linux:   ``bash -c "echo | <payload>"``     (list olarak build_command icinde)

    Bu fonksiyon sadece ic payload string'ini dondurur.
    """
    return f"echo | {payload}"


def build_echo_pipe_command(payload: str) -> list[str]:
    """``echo | <payload>`` komutunu platform uyumlu list olarak dondurur.

    Ornek (Linux):  ``["bash", "-c", "echo | openssl ..."]``
    Ornek (Windows): ``["cmd.exe", "/c", "echo | openssl ..."]``
    """
    full_cmd = pipe_echo_cmd(payload)
    if is_windows():
        return ["cmd.exe", "/c", full_cmd]
    return ["bash", "-c", full_cmd]


# Module-level cached encoding
CONSOLE_ENCODING: str = get_console_encoding()
