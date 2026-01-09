# SENTINEL AI - Docker Runner
# Sprint 2: Docker container içinde komut çalıştırma
#
# Bu modül, güvenlik araçlarını Docker container içinde çalıştırır.
# Container: sentinel-tools (Ubuntu + Nmap, Gobuster, Nikto, Hydra)

import subprocess
from typing import List, Tuple, Optional


CONTAINER_NAME = "sentinel-tools"


def is_container_running() -> bool:
    """
    sentinel-tools container'ının çalışıp çalışmadığını kontrol et.
    
    Returns:
        True: Container çalışıyor
        False: Container çalışmıyor veya yok
    """
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() == "true"
    except Exception:
        return False


def get_docker_command(tool: str, args: List[str]) -> Tuple[str, List[str]]:
    """
    Docker exec komutu oluştur.
    
    Args:
        tool: Çalıştırılacak araç (nmap, gobuster, etc.)
        args: Araç argümanları
    
    Returns:
        (command, args) tuple - QProcess.start() için hazır
    
    Örnek:
        tool="nmap", args=["-sS", "192.168.1.1"]
        -> ("docker", ["exec", "sentinel-tools", "nmap", "-sS", "192.168.1.1"])
    """
    docker_args = ["exec", CONTAINER_NAME, tool] + args
    return ("docker", docker_args)


def run_command_sync(tool: str, args: List[str], timeout: int = 300) -> Tuple[int, str, str]:
    """
    Komutu senkron olarak çalıştır (test için).
    
    Args:
        tool: Çalıştırılacak araç
        args: Araç argümanları
        timeout: Maksimum bekleme süresi (saniye)
    
    Returns:
        (exit_code, stdout, stderr)
    
    Not: UI'da kullanma! QProcess ile async çalıştır.
    """
    command, docker_args = get_docker_command(tool, args)
    
    try:
        result = subprocess.run(
            [command] + docker_args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return (result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (-1, "", "Timeout: Komut çok uzun sürdü")
    except Exception as e:
        return (-1, "", f"Hata: {str(e)}")


def list_available_tools() -> List[str]:
    """
    Container'da mevcut araçları listele.
    
    Returns:
        Araç isimleri listesi
    """
    tools = ["nmap", "gobuster", "nikto", "hydra", "sqlmap", "dirb", "whois", "dig"]
    available = []
    
    for tool in tools:
        try:
            result = subprocess.run(
                ["docker", "exec", CONTAINER_NAME, "which", tool],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                available.append(tool)
        except Exception:
            pass
    
    return available


# =============================================================================
# Yiğit İçin Kullanım Örneği
# =============================================================================
#
# from src.core.docker_runner import get_docker_command, is_container_running
#
# # Container kontrolü
# if not is_container_running():
#     print("Hata: sentinel-tools container çalışmıyor!")
#     print("Çalıştır: docker compose up -d tools-service")
#     return
#
# # Komutu hazırla
# tool = "nmap"
# args = ["-sS", "-p-", "192.168.1.100"]
# command, docker_args = get_docker_command(tool, args)
#
# # QProcess ile çalıştır
# self._process_manager.start_process(command, docker_args)
#

