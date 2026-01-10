# 🔬 Sprint 3 Kritik Mimari Analiz

**Tarih:** 9 Ocak 2026  
**Hazırlayan:** Yiğit  
**Konu:** Güvenli Yetki Yönetimi ve Kaynak Temizliği - Mimari Karar Noktası

---

## 📌 Özet

Sprint 3'e başlamadan önce kritik bir mimari karar vermemiz gerekiyor. Mevcut Docker-tabanlı mimarimiz ile planlanan pkexec-tabanlı yetki yönetimi arasında bir çelişki var.

---

## 🚨 Tespit Edilen Kritik Sorun: Docker vs pkexec Çatışması

### Mevcut Mimari (Docker Modu)

```
Kullanıcı → main.py → docker exec sentinel-tools nmap -sS target
                      ↓
              Container içinde root olarak çalışır
              Dosyalar container'ın /app/output/ içinde kalır
              pkexec GEREKMİYOR
```

**Mevcut Kod (main.py - _on_approve_command):**
```python
if is_container_running():
    command, docker_args = get_docker_command(cmd.tool, args)
    self._process_manager.start_process(command, docker_args, requires_root=False)
else:
    self._process_manager.start_process(cmd.tool, args, requires_root=cmd.requires_root)
```

### Planlanan Mimari (Native/pkexec Modu)

```
Kullanıcı → main.py → pkexec nmap -sS target
                      ↓
              Host sistemde root olarak çalışır
              Dosyalar host'un /tmp/ içinde kalır
              pkexec GEREKLİ
```

---

## 🤔 Karar Noktası: Hangi Mimariyi Seçeceğiz?

### Seçenek 1: Sadece Docker Modu

| Avantajlar | Dezavantajlar |
|------------|---------------|
| ✅ İzolasyon (güvenlik) | ❌ Docker kurulu olmalı |
| ✅ Taşınabilirlik (her yerde aynı çalışır) | ❌ Container kaynak tüketimi |
| ✅ Root yönetimi Docker'a bırakılır | ❌ Bazı network taramaları host mode gerektirir |
| ✅ pkexec karmaşıklığı yok | ❌ macOS/Windows'ta network kısıtlamaları |
| ✅ Araçlar her zaman mevcut | |

**Ne Zaman Uygun:**
- Kullanıcı Docker kurabiliyorsa
- Taşınabilirlik önemliyse
- Güvenlik öncelikliyse

### Seçenek 2: Sadece Native (pkexec) Modu

| Avantajlar | Dezavantajlar |
|------------|---------------|
| ✅ Daha hızlı (container overhead yok) | ❌ Araçların host'a kurulu olması gerekir |
| ✅ Tam network erişimi | ❌ pkexec yönetimi karmaşık |
| ✅ Docker bağımlılığı yok | ❌ Root dosya temizliği problemi |
| ✅ Düşük kaynak tüketimi | ❌ Her Linux dağıtımında farklı davranabilir |
| | ❌ Windows/macOS desteği yok |

**Ne Zaman Uygun:**
- Sadece Linux hedefleniyorsa
- Docker kurulamıyorsa
- Performans kritikse

### Seçenek 3: Hibrit Mod ⭐ (ÖNERİLEN)

```
Docker çalışıyor mu?
  ├── EVET → Docker modu (pkexec gerekmez)
  └── HAYIR → Native mod (pkexec gerekli, sadece Linux)
```

| Avantajlar | Dezavantajlar |
|------------|---------------|
| ✅ Maksimum esneklik | ❌ Daha fazla kod karmaşıklığı |
| ✅ Kullanıcı tercihine göre çalışır | ❌ İki modu da test etmek gerekir |
| ✅ Fallback mekanizması | ❌ Edge case'ler artabilir |
| ✅ Farklı deployment senaryolarına uyum | |

**Ne Zaman Uygun:**
- Geniş kullanıcı kitlesine hitap edilecekse
- Hem Docker hem de native kullanıcılar varsa

---

## 📋 Hibrit Mod Detaylı Mimari Planı

### Yeni Modül: ExecutionManager

**Dosya:** `src/core/execution_manager.py`

```python
from enum import Enum
from typing import Tuple, List, Optional
import os
import platform

class ExecutionMode(Enum):
    DOCKER = "docker"      # Container içinde çalıştır
    NATIVE = "native"      # Host'ta direkt çalıştır

class ExecutionManager:
    """
    Çalıştırma modunu yöneten merkezi sınıf.
    Docker varsa Docker modu, yoksa Native mod kullanır.
    """
    
    def __init__(self):
        self._mode = self._detect_mode()
        self._platform = platform.system()  # 'Linux', 'Windows', 'Darwin'
    
    @property
    def mode(self) -> ExecutionMode:
        return self._mode
    
    @property
    def is_linux(self) -> bool:
        return self._platform == "Linux"
    
    def _detect_mode(self) -> ExecutionMode:
        """Docker varsa DOCKER, yoksa NATIVE mod"""
        from src.core.docker_runner import is_container_running
        if is_container_running():
            return ExecutionMode.DOCKER
        return ExecutionMode.NATIVE
    
    def can_run_privileged(self) -> bool:
        """Yüksek yetkili komut çalıştırılabilir mi?"""
        if self._mode == ExecutionMode.DOCKER:
            return True  # Container zaten root
        elif self._platform == "Linux":
            return self._check_pkexec_available()
        else:
            return False  # Windows/macOS'ta pkexec yok
    
    def _check_pkexec_available(self) -> bool:
        """pkexec kurulu mu kontrol et"""
        import shutil
        return shutil.which("pkexec") is not None
    
    def prepare_command(
        self, 
        tool: str, 
        args: List[str], 
        requires_root: bool = False
    ) -> Tuple[str, List[str], Optional[str]]:
        """
        Moda göre komutu hazırla.
        
        Returns:
            (command, args, temp_output_path)
        """
        if self._mode == ExecutionMode.DOCKER:
            from src.core.docker_runner import get_docker_command
            cmd, docker_args = get_docker_command(tool, args)
            return (cmd, docker_args, "/app/output/")
        else:
            if requires_root and self.is_linux:
                return ("pkexec", [tool] + args, "/tmp/")
            return (tool, args, "/tmp/")
    
    def get_temp_path(self, filename: str) -> str:
        """Moda göre geçici dosya yolu üret"""
        import uuid
        safe_filename = f"sentinel_{uuid.uuid4().hex[:8]}_{filename}"
        
        if self._mode == ExecutionMode.DOCKER:
            return f"/app/output/{safe_filename}"
        else:
            return f"/tmp/{safe_filename}"
```

### Güncellenmiş: SecureCleaner

**Dosya:** `src/core/cleaner.py`

```python
import os
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

class SecureCleaner:
    """
    Güvenli dosya temizleme ve session yönetimi.
    
    Güvenlik Özellikleri:
    - Path traversal koruması
    - Güvenli silme (overwrite + delete)
    - Root dosyaları için pkexec fallback
    """
    
    # İzin verilen temizlik dizinleri (whitelist)
    ALLOWED_PATHS = [
        "/tmp/sentinel_",
        "/app/output/sentinel_",
        "temp/session_",
    ]
    
    def __init__(self, execution_manager=None):
        self._exec_mgr = execution_manager
    
    def delete(self, file_path: str, secure: bool = True) -> bool:
        """
        Dosyayı güvenli şekilde sil.
        
        Args:
            file_path: Silinecek dosya yolu
            secure: True ise üzerine yaz sonra sil
        
        Returns:
            True: Başarılı
            False: Başarısız
        """
        # Güvenlik kontrolü
        if not self._is_safe_path(file_path):
            raise SecurityError(f"Güvensiz path reddedildi: {file_path}")
        
        # Dosya var mı?
        if not os.path.exists(file_path):
            return True  # Zaten yok
        
        try:
            if secure:
                self._secure_overwrite(file_path)
            os.remove(file_path)
            return True
        except PermissionError:
            # Root dosyası - pkexec ile dene
            return self._privileged_delete(file_path)
        except Exception as e:
            print(f"Silme hatası: {e}")
            return False
    
    def _is_safe_path(self, path: str) -> bool:
        """
        Path traversal ve güvenlik kontrolü.
        
        Kontroller:
        1. Whitelist'te mi?
        2. '..' içeriyor mu?
        3. Symlink mi?
        4. Absolute path mi?
        """
        # Normalize path
        real_path = os.path.realpath(path)
        
        # '..' kontrolü
        if '..' in path:
            return False
        
        # Symlink kontrolü (TOCTOU önlemi)
        if os.path.islink(path):
            return False
        
        # Whitelist kontrolü
        for allowed in self.ALLOWED_PATHS:
            if real_path.startswith(allowed) or path.startswith(allowed):
                return True
        
        return False
    
    def _secure_overwrite(self, file_path: str):
        """Dosyayı rastgele veriyle üzerine yaz (kurtarmayı zorlaştırır)"""
        try:
            file_size = os.path.getsize(file_path)
            with open(file_path, 'wb') as f:
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            pass  # Üzerine yazma başarısız olsa bile silmeyi dene
    
    def _privileged_delete(self, file_path: str) -> bool:
        """pkexec rm ile sil (Linux only)"""
        if not self._exec_mgr or self._exec_mgr.mode != ExecutionMode.NATIVE:
            return False
        
        if not self._exec_mgr.is_linux:
            return False
        
        import subprocess
        try:
            result = subprocess.run(
                ["pkexec", "rm", "-f", file_path],
                capture_output=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def cleanup_old_sessions(self, days: int = 7) -> int:
        """
        Belirtilen günden eski session dosyalarını temizle.
        
        Returns:
            Silinen dosya sayısı
        """
        temp_dir = Path("temp")
        if not temp_dir.exists():
            return 0
        
        deleted = 0
        cutoff = datetime.now() - timedelta(days=days)
        
        for file in temp_dir.glob("session_*.txt"):
            try:
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                if mtime < cutoff:
                    if self.delete(str(file), secure=False):
                        deleted += 1
            except Exception:
                continue
        
        return deleted
    
    def cleanup_by_size(self, max_mb: int = 100) -> int:
        """
        Toplam boyut aşılırsa en eski dosyaları sil.
        
        Returns:
            Silinen dosya sayısı
        """
        temp_dir = Path("temp")
        if not temp_dir.exists():
            return 0
        
        files = list(temp_dir.glob("session_*.txt"))
        total_size = sum(f.stat().st_size for f in files)
        max_bytes = max_mb * 1024 * 1024
        
        if total_size <= max_bytes:
            return 0
        
        # Eskiden yeniye sırala
        files.sort(key=lambda f: f.stat().st_mtime)
        
        deleted = 0
        while total_size > max_bytes and files:
            oldest = files.pop(0)
            size = oldest.stat().st_size
            if self.delete(str(oldest), secure=False):
                total_size -= size
                deleted += 1
        
        return deleted
    
    def get_stats(self) -> dict:
        """Session istatistiklerini döndür"""
        temp_dir = Path("temp")
        if not temp_dir.exists():
            return {"count": 0, "total_size_mb": 0, "oldest": None, "newest": None}
        
        files = list(temp_dir.glob("session_*.txt"))
        if not files:
            return {"count": 0, "total_size_mb": 0, "oldest": None, "newest": None}
        
        files.sort(key=lambda f: f.stat().st_mtime)
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            "count": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest": files[0].name,
            "newest": files[-1].name
        }


class SecurityError(Exception):
    """Güvenlik ihlali hatası"""
    pass
```

---

## ⚠️ Kritik Risk Analizi

### Risk 1: Path Traversal Attack
| Risk | Seviye | Önlem |
|------|--------|-------|
| `pkexec rm /etc/passwd` çalıştırılması | 🔴 KRİTİK | Whitelist path kontrolü, realpath kontrolü |

### Risk 2: Race Condition (TOCTOU)
| Risk | Seviye | Önlem |
|------|--------|-------|
| Dosya okunurken başkası tarafından değiştirilmesi | 🟡 ORTA | File locking, symlink kontrolü |

### Risk 3: pkexec Timeout
| Risk | Seviye | Önlem |
|------|--------|-------|
| Kullanıcı parola penceresini açık bırakır | 🟢 DÜŞÜK | QProcess timeout, iptal butonu |

### Risk 4: Docker Socket Güvenliği
| Risk | Seviye | Önlem |
|------|--------|-------|
| Docker socket erişimi = host root | 🟡 ORTA | Non-root container (ileride) |

### Risk 5: Windows/macOS Uyumluluğu
| Risk | Seviye | Önlem |
|------|--------|-------|
| pkexec sadece Linux'ta var | 🟡 ORTA | Platform detection, graceful degradation |

---

## 📊 Görev Listesi ve Öncelikler

| # | Görev | Dosya | Sorumlu | Öncelik | Bağımlılık |
|---|-------|-------|---------|---------|------------|
| 1 | ExecutionManager | `src/core/execution_manager.py` | Yiğit | 🔴 KRİTİK | - |
| 2 | InputValidator | `src/core/validators.py` | Yiğit | 🟡 YÜKSEK | - |
| 3 | SecureCleaner | `src/core/cleaner.py` | Yiğit | 🔴 KRİTİK | ExecutionManager |
| 4 | ProcessManager Update | `src/core/process_manager.py` | Yiğit | 🟡 YÜKSEK | ExecutionManager |
| 5 | main.py Entegrasyon | `main.py` | Yiğit | 🟢 ORTA | Hepsi |

---

## ❓ Kerem'e Sorular

1. **Hangi mimariyi tercih ediyorsun?**
   - [ ] Sadece Docker
   - [ ] Sadece Native (pkexec)
   - [ ] Hibrit (önerilen)

2. **Session saklama süresi ne olsun?**
   - [ ] 3 gün
   - [ ] 7 gün (önerilen)
   - [ ] 14 gün
   - [ ] Kullanıcı ayarlasın

3. **Windows/macOS desteği gerekli mi?**
   - [ ] Evet, ilk sürümden itibaren
   - [ ] Hayır, sadece Linux (önerilen)
   - [ ] İleride eklenebilir

4. **Sprint 4'teki nmap XML parsing ile entegrasyon:**
   - XML dosyaları nerede saklanacak?
   - Dosya formatı: `/tmp/sentinel_<uuid>_scan.xml` uygun mu?

---

## 🗓️ Zaman Tahmini

| Görev | Tahmini Süre |
|-------|-------------|
| ExecutionManager | 2-3 saat |
| SecureCleaner | 3-4 saat |
| InputValidator | 1-2 saat |
| ProcessManager güncelleme | 2-3 saat |
| main.py entegrasyon | 2-3 saat |
| Test | 2-3 saat |
| **TOPLAM** | **12-18 saat** |

---

## ✅ Sonraki Adımlar

1. Bu dokümanı Kerem ile paylaş
2. Mimari karar verilsin (Docker/Native/Hibrit)
3. Karara göre Sprint 3'ü başlat
4. Her modül için ayrı branch aç
5. Code review sonrası develop'a merge

---

*Doküman Versiyonu: 1.0*  
*Son Güncelleme: 9 Ocak 2026*
