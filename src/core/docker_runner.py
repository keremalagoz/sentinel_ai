# SENTINEL AI - Docker Runner
# Sprint 2: Docker container içinde komut çalıştırma
#
# Bu modül, güvenlik araçlarını Docker container içinde çalıştırır.
# Container: sentinel-tools (Ubuntu + Nmap, Gobuster, Nikto, Hydra)

import subprocess
from typing import List, Tuple, Optional
import time


CONTAINER_NAME = "sentinel-tools"

# Cache for list_available_tools (container basladiginda bir kez kontrol edilir)
_tools_cache = None
_tools_cache_valid = False

# Cache for is_container_running (kısa TTL + hata backoff)
_container_running_cache: Optional[bool] = None
_container_cache_time = 0.0
_container_cache_ttl = 1.5
_container_backoff_until = 0.0


def is_container_running() -> bool:
    """
    sentinel-tools container'ının çalışıp çalışmadığını kontrol et.
    
    Returns:
        True: Container çalışıyor
        False: Container çalışmıyor veya yok
    """
    global _container_running_cache, _container_cache_time, _container_backoff_until

    now = time.time()

    # Backoff penceresinde tekrar docker çağrısı yapma
    if now < _container_backoff_until:
        return bool(_container_running_cache)

    # TTL içindeyse cache dön
    if _container_running_cache is not None and (now - _container_cache_time) < _container_cache_ttl:
        return _container_running_cache

    try:
        # Timeout ekle: Docker daemon yanıt vermezse UI donmasın (2 sn yeterli)
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME],
            capture_output=True,
            text=True,
            timeout=2
        )
        is_running = result.stdout.strip() == "true"
        _container_running_cache = is_running
        _container_cache_time = now
        return is_running
    except subprocess.TimeoutExpired:
        _container_running_cache = False
        _container_cache_time = now
        _container_backoff_until = now + 2.0
        return False
    except Exception:
        _container_running_cache = False
        _container_cache_time = now
        _container_backoff_until = now + 2.0
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


def list_available_tools(force_refresh: bool = False) -> List[str]:
    """
    Container'da mevcut araçları listele (cache mekanizmalı).
    
    Args:
        force_refresh: True ise cache'i atla ve yeniden kontrol et
    
    Returns:
        Araç isimleri listesi
    """
    global _tools_cache, _tools_cache_valid
    
    # Cache gecerli mi?
    if _tools_cache_valid and not force_refresh and _tools_cache is not None:
        return _tools_cache
    
    tools = ["nmap", "gobuster", "nikto", "hydra", "sqlmap", "dirb", "whois", "dig"]
    available = []
    
    for tool in tools:
        try:
            result = subprocess.run(
                ["docker", "exec", CONTAINER_NAME, "which", tool],
                capture_output=True,
                text=True,
                timeout=2  # Hızlı kontrol
            )
            if result.returncode == 0:
                available.append(tool)
        except Exception:
            pass
    
    # Cache guncelle
    _tools_cache = available
    _tools_cache_valid = True
    
    return available


def invalidate_tools_cache():
    """Container yeniden basladiginda cache'i sifirla."""
    global _tools_cache_valid, _container_running_cache, _container_cache_time, _container_backoff_until
    _tools_cache_valid = False
    _container_running_cache = None
    _container_cache_time = 0.0
    _container_backoff_until = 0.0


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

