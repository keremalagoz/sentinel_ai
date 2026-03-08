
import os
import shutil
import platform
import random
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta

# Execution Manager ile entegre çalışacak
from src.core.execution_manager import get_execution_manager, ExecutionMode

class SecureCleaner:
    """
    Güvenli dosya temizleme ve session yönetimi.
    
    Güvenlik Özellikleri:
    - Path traversal koruması (.., /etc/passwd vb. yasak)
    - Güvenli silme (overwrite + delete)
    - Root dosyaları için pkexec fallback (Linux only)
    """
    
    def __init__(self):
        self._exec_mgr = get_execution_manager()
        
        # İzin verilen temizlik dizinleri (Whitelist)
        # Bu dizinlerin dışındaki hiçbir dosya silinmez!
        self.ALLOWED_PATHS = [
            "/tmp/sentinel_",          # Linux temp
            "/app/output/sentinel_",   # Docker container path
            "temp/session_",           # Proje içi loglar
        ]
        
        # Windows için temp path ekle
        if self._exec_mgr.is_windows:
            win_temp = os.path.join(os.environ.get("TEMP", ""), "sentinel")
            self.ALLOWED_PATHS.append(win_temp)
    
    def delete(self, file_path: str, secure: bool = True) -> bool:
        """
        Dosyayı güvenli şekilde siler.
        
        Args:
            file_path: Silinecek dosya yolu (absolute veya relative)
            secure: True ise dosyayı önce overwrite eder (Shredding)
        """
        # Güvenlik Kontrolü 1: Path Traversal
        if not self._is_safe_path(file_path):
            print(f"[BLOCKED] GUVENLIK UYARISI: {file_path} silinmesi engellendi (Whitelist disi).")
            return False
            
        if not os.path.exists(file_path):
            return True # Zaten yok
            
        try:
            # Önce güvenli silme (Overwrite)
            if secure:
                self._secure_overwrite(file_path)
            
            # Normal silme
            os.remove(file_path)
            return True
            
        except PermissionError:
            # Yetki hatası: Dosya root'a ait olabilir.
            # Sadece Linux ve Native modda ise pkexec dene
            return self._privileged_delete(file_path)
            
        except Exception as e:
            print(f"[ERROR] Silme hatasi ({file_path}): {e}")
            return False

    def _is_safe_path(self, path: str) -> bool:
        """
        Bu path'in silinmesi güvenli mi?
        """
        # 1. Path normalizasyonu (../ gibi şeyleri çöz)
        real_path = os.path.abspath(path)
        
        # 2. Whitelist kontrolü
        # Windows path'leri için case-insensitive kontrol yapılmalı
        check_path = real_path.lower() if self._exec_mgr.is_windows else real_path
        
        for allowed in self.ALLOWED_PATHS:
            allowed_norm = os.path.abspath(allowed).lower() if self._exec_mgr.is_windows else os.path.abspath(allowed)
            
            # Directory prefix kontrolü (örn: /tmp/sentinel_...)
            if check_path.startswith(allowed_norm):
                return True
                
        # Proje içi temp klasörü kontrolü (Relative path)
        project_temp = os.path.abspath("temp")
        if check_path.startswith(project_temp.lower() if self._exec_mgr.is_windows else project_temp):
            return True
            
        return False
        
    def _secure_overwrite(self, file_path: str):
        """
        Dosyanın içeriğini rastgele byte'larla doldurur.
        SSD'lerde %100 garanti vermez ama HDD'lerde kurtarmayı zorlaştırır.
        """
        try:
            length = os.path.getsize(file_path)
            # 1MB altı dosyalar için tam overwrite, büyükler için başını boz
            write_len = min(length, 1024 * 1024) 
            
            with open(file_path, "rb+") as f:
                f.write(os.urandom(write_len))
        except Exception:
            pass # Overwrite hatası kritik değil, silmeye devam et

    def _privileged_delete(self, file_path: str) -> bool:
        """
        Linux'ta 'pkexec rm' kullanarak root dosyalarını siler.
        """
        if not self._exec_mgr.is_linux:
            return False # Windows'ta UAC prompt açamayız (şu an için)
            
        if self._exec_mgr.mode == ExecutionMode.DOCKER:
            return False # Docker'da ise container içinden silinmeliydi, host'tan değil
            
        # Pkexec çağrısı (Timeout ekli)
        import subprocess
        try:
            subprocess.run(
                ["pkexec", "rm", "-f", file_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5 # 5 saniye içinde şifre girilmezse iptal
            )
            return True
        except subprocess.TimeoutExpired:
            print(f"[WARNING] Pkexec timeout: {file_path}")
            return False
        except Exception:
            return False

    def cleanup_old_sessions(self, days: int = 7, secure_delete: bool = False) -> int:
        """
        Eski session loglarını (sentinel_*, session_*) temizler.
        System temp + proje ici temp dizinlerini birlikte tarar.
        """
        deleted_count = 0
        cutoff = datetime.now() - timedelta(days=days)

        project_temp_dir = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp"))

        candidate_dirs: List[Path] = [project_temp_dir]
        if self._exec_mgr.is_windows:
            candidate_dirs.append(Path(os.path.join(os.environ.get("TEMP", ""), "sentinel")))
        elif self._exec_mgr.is_linux:
            candidate_dirs.append(Path("/tmp"))

        seen_paths = set()
        for target_dir in candidate_dirs:
            if not target_dir.exists():
                continue
            for pattern in ("sentinel_*", "session_*"):
                for item in target_dir.glob(pattern):
                    try:
                        real_item = str(item.resolve())
                    except Exception:
                        real_item = str(item)

                    if real_item in seen_paths:
                        continue
                    seen_paths.add(real_item)

                    if not item.is_file():
                        continue

                    try:
                        mtime = datetime.fromtimestamp(item.stat().st_mtime)
                        if mtime < cutoff and self.delete(str(item), secure=secure_delete):
                            deleted_count += 1
                    except Exception:
                        continue

        # Ayrica chat_history.json dosyasini da temizle (Proje ici temp dizininde bulunur)
        chat_history_path = project_temp_dir / "chat_history.json"
        
        if chat_history_path.exists():
            try:
                import json
                with open(chat_history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                
                new_history = []
                for chat in history:
                    if not chat.get('messages'):
                        deleted_count += 1
                        continue

                    chat_date_str = chat.get('date')
                    keep = True
                    if chat_date_str:
                        try:
                            chat_date = datetime.strptime(chat_date_str, "%Y-%m-%d %H:%M")
                            if chat_date < cutoff:
                                keep = False
                                deleted_count += 1
                        except Exception:
                            pass
                    
                    if keep:
                        new_history.append(chat)
                        
                if len(new_history) != len(history):
                    with open(chat_history_path, 'w', encoding='utf-8') as f:
                        json.dump(new_history, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[WARN] Chat history cleanup failed: {e}")
                
        return deleted_count

# Global instance
_cleaner = SecureCleaner()

def get_cleaner() -> SecureCleaner:
    return _cleaner
