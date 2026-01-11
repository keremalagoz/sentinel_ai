# SENTINEL AI - UI ve Core İyileştirme Görevleri (Yiğit)

Sen Yiğit'sin (System/UI/Security sorumlusu). Sprint 0-3 kapsamında UI, Core ve güvenlik modüllerinde tespit edilen sorunları düzeltmelisin.

## 🎯 GÖREV LİSTESİ (Öncelik Sırasına Göre)

### 🔴 P0 - Kritik (Bugün/Yarın)

#### 1. Emoji Karakterlerini Temizle (AGENT_RULES.md İhlali)
**Dosya:** `main.py`
**Sorun:** Windows console encoding (cp1252) emoji desteklemiyor, crash riski var.

**Değişiklikler:**

```python
# Satır 185 - DEĞİŞTİR
# ÖNCESİ:
title = QLabel("⚔️ SENTINEL AI")

# SONRASI:
title = QLabel(">>> SENTINEL AI")

# Satır 224 - DEĞİŞTİR
# ÖNCESİ:
target_label = QLabel("🎯 Hedef:")

# SONRASI:
target_label = QLabel("[TARGET] Hedef:")

# Satır 237 - DEĞİŞTİR
# ÖNCESİ:
ai_label = QLabel("🤖 Komut:")

# SONRASI:
ai_label = QLabel("[AI] Komut:")

# Satır 269 - DEĞİŞTİR
# ÖNCESİ:
self._approval_title = QLabel("🔍 AI Önerisi")

# SONRASI:
self._approval_title = QLabel("[ANALYSIS] AI Önerisi")

# Satır 302 - DEĞİŞTİR
# ÖNCESİ:
self._btn_reject = QPushButton("✕ İptal")

# SONRASI:
self._btn_reject = QPushButton("[X] İptal")

# Satır 309 - DEĞİŞTİR
# ÖNCESİ:
self._btn_approve = QPushButton("✓ Çalıştır")

# SONRASI:
self._btn_approve = QPushButton("[OK] Çalıştır")
```

**AYRICA:** `terminal_view.py` kontrol et:
```python
# src/ui/terminal_view.py - emoji kullanımı var mı kontrol et
# Satır 118-129'da butonlar var, emoji yok - ✅ Temiz
```

---

#### 2. Process Manager Type Hints Ekleme
**Dosya:** `src/core/process_manager.py`
**Sorun:** Fonksiyonlarda return type yok.

**Değişiklikler:**

```python
# Dosya başına ekle (satır 1'den sonra)
from typing import Optional

# Satır 34 - DEĞİŞTİR
def start_process(self, command: str, args: list, requires_root: bool = False):
# SONRASI:
def start_process(self, command: str, args: List[str], requires_root: bool = False) -> None:

# Satır 70 - DEĞİŞTİR
def write_input(self, text: str):
# SONRASI:
def write_input(self, text: str) -> None:

# Satır 85 - DEĞİŞTİR
def stop_process(self):
# SONRASI:
def stop_process(self) -> None:

# Satır 91 - DEĞİŞTİR
def _handle_stdout(self):
# SONRASI:
def _handle_stdout(self) -> None:

# Satır 107 - DEĞİŞTİR
def _handle_stderr(self):
# SONRASI:
def _handle_stderr(self) -> None:

# Satır 118 - DEĞİŞTİR
def _handle_finished(self, exit_code: int, exit_status):
# SONRASI:
def _handle_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:

# Satır 137 - DEĞİŞTİR
def is_running(self) -> bool:  # ✅ Zaten var
    ...
```

---

#### 3. Execution Manager Düzeltmeleri
**Dosya:** `src/core/execution_manager.py`
**Sorun:** `_time` property kafa karıştırıcı, import anti-pattern.

**Değişiklikler:**

```python
# Dosya başına ekle (satır 1-6 arasına)
import time  # EKLE (en üste)

# Satır 22-23 - SİL
import time  # Bu satırı sil (class içindeki import)

# Satır 36 - DEĞİŞTİR
# ÖNCESİ:
@property
def mode(self) -> ExecutionMode:
    # Getter çağrıldığında TTL kontrolü yap
    if (self._time.time() - self._last_check) > self._check_ttl:
        self._update_mode()
    return self._mode

# SONRASI:
@property
def mode(self) -> ExecutionMode:
    """Execution modunu döndürür (cache ile)."""
    if (time.time() - self._last_check) > self._check_ttl:
        self._update_mode()
    return self._mode

# Satır 41-43 - SİL
@property
def _time(self):
    import time
    return time
# Bu property'yi komple sil

# Satır 56 - DEĞİŞTİR
def _update_mode(self):
    """Modu günceller ve zaman damgasını yeniler"""
    self._mode = self._detect_mode()
    self._last_check = self._time.time()  # ÖNCESİ

def _update_mode(self) -> None:
    """Modu günceller ve zaman damgasını yeniler"""
    self._mode = self._detect_mode()
    self._last_check = time.time()  # SONRASI

# Diğer type hint eklemeleri:
# Satır 58 - DEĞİŞTİR
def _detect_mode(self) -> ExecutionMode:  # ✅ Zaten var

# Satır 73 - DEĞİŞTİR
def can_run_privileged(self) -> bool:  # ✅ Zaten var

# Satır 91 - DEĞİŞTİR
def prepare_command(
    self, 
    tool: str, 
    args: List[str], 
    requires_root: bool = False
) -> Tuple[str, List[str], str]:  # ✅ Zaten var

# Satır 131 - DEĞİŞTİR
def get_temp_path(self, filename: str) -> str:  # ✅ Zaten var
```

---

#### 4. Cleaner Exception Handling İyileştirmesi
**Dosya:** `src/core/cleaner.py`
**Sorun:** Genel `except Exception` kullanımı.

**Değişiklikler:**

```python
# Satır 69-71 - DEĞİŞTİR
# ÖNCESİ:
except Exception as e:
    print(f"[ERROR] Silme hatasi ({file_path}): {e}")
    return False

# SONRASI:
except (OSError, IOError) as e:
    # Dosya sistemi hataları
    print(f"[ERROR] Silme hatasi ({file_path}): {e}")
    return False
except Exception as e:
    # Beklenmeyen hatalar
    print(f"[CRITICAL] Unexpected error in delete ({file_path}): {e}")
    return False

# Satır 110-111 - DEĞİŞTİR
# ÖNCESİ:
except Exception:
    pass  # Overwrite hatası kritik değil

# SONRASI:
except (OSError, IOError):
    # Overwrite hatası kritik değil, silmeye devam et
    pass

# Satır 137-138 - DEĞİŞTİR
# ÖNCESİ:
except Exception:
    return False

# SONRASI:
except (subprocess.CalledProcessError, FileNotFoundError):
    return False

# Satır 170 - DEĞİŞTİR
# ÖNCESİ:
except Exception:
    continue

# SONRASI:
except (OSError, PermissionError):
    # Dosya silinemedi, devam et
    continue
```

---

### 🟡 P1 - Yüksek (Bu Hafta)

#### 5. QProcess Error Handling Ekleme
**Dosya:** `src/core/process_manager.py`
**Sorun:** `QProcess.errorOccurred` sinyali yakalanmıyor.

**Değişiklikler:**

```python
# Satır 30-32 - SONRASINA EKLE
self._process.readyReadStandardOutput.connect(self._handle_stdout)
self._process.readyReadStandardError.connect(self._handle_stderr)
self._process.finished.connect(self._handle_finished)
# EKLE:
self._process.errorOccurred.connect(self._handle_error)

# Satır 140'tan sonra YENİ METOD EKLE:
def _handle_error(self, error: QProcess.ProcessError) -> None:
    """
    QProcess hata durumunda çağrılır.
    
    Hata tipleri:
    - FailedToStart: Komut bulunamadı veya çalıştırılamadı
    - Crashed: Process beklenmedik şekilde sonlandı
    - Timedout: Zaman aşımı
    - WriteError: Process'e yazılamadı
    - ReadError: Process'ten okunamadı
    """
    error_messages = {
        QProcess.ProcessError.FailedToStart: "Komut bulunamadi veya calistirilamadi",
        QProcess.ProcessError.Crashed: "Process beklenmedik sekilde sonlandi",
        QProcess.ProcessError.Timedout: "Process zaman asimina ugradi",
        QProcess.ProcessError.WriteError: "Process'e yazilamadi",
        QProcess.ProcessError.ReadError: "Process'ten okunamadi",
    }
    msg = error_messages.get(error, "Bilinmeyen hata")
    error_text = f"[ERROR] QProcess Hatasi: {msg}\n"
    
    # Terminal'e hata mesajı gönder
    self.sig_output_stream.emit(error_text, "stderr")
    
    # Log'a da yaz (eğer log file açıksa)
    if self._log_file:
        self._log_file.write(error_text)
        self._log_file.flush()
```

---

#### 6. Terminal View Buffer Limiti Ekleme
**Dosya:** `src/ui/terminal_view.py`
**Sorun:** Uzun çıktılarda (nmap -p-) buffer sınırsız, RAM tüketimi artar.

**Değişiklikler:**

```python
# Satır 45 - __init__ içine EKLE (self._history_index = 0'dan sonra)
self._command_history = []
self._history_index = 0
# EKLE:
self._max_buffer_lines = 10000  # Maksimum satır sayısı

# Satır 287-300 - _on_output metodunu GÜNCELLE
@pyqtSlot(str, str)
def _on_output(self, text: str, channel: str):
    """Handle process output."""
    if self._current_mode == self.MODE_IDLE:
        self._set_mode(self.MODE_RUNNING)
    
    self._detect_prompt(text)
    
    color = Colors.DANGER if channel == "stderr" else Colors.TEXT_PRIMARY
    cursor = self._output.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertHtml(f"<span style='color: {color};'>{self._escape(text)}</span>")
    self._output.setTextCursor(cursor)
    self._output.ensureCursorVisible()
    
    # EKLE: Buffer limiti kontrolü
    doc = self._output.document()
    if doc.lineCount() > self._max_buffer_lines:
        # İlk 1000 satırı sil
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        for _ in range(1000):
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            if cursor.atEnd():
                break
            cursor.deleteChar()  # Newline'ı da sil
        
        # Bilgi mesajı ekle
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.insertHtml(f"<span style='color: {Colors.WARNING};'>[BUFFER] İlk 1000 satır temizlendi (limit: {self._max_buffer_lines})</span><br>")
```

---

#### 7. Validators Type Hints Ekleme
**Dosya:** `src/core/validators.py`
**Sorun:** Fonksiyonlarda return type yok.

**Değişiklikler:**

```python
# Satır 27-37 - DEĞİŞTİR
@staticmethod
def validate_ip(ip: str) -> bool:  # ✅ Zaten var

# Satır 40-65 - DEĞİŞTİR
@staticmethod
def validate_hostname(hostname: str) -> bool:  # ✅ Zaten var

# Satır 68-77 - DEĞİŞTİR
@staticmethod
def sanitize(text: str) -> str:  # ✅ Zaten var

# Satır 80-84 - DEĞİŞTİR
@staticmethod
def is_safe_arg(arg: str) -> bool:  # ✅ Zaten var

# Satır 87-95 - DEĞİŞTİR
@staticmethod
def validate_target(target: str) -> bool:  # ✅ Zaten var

# Bu dosya temiz, değişiklik gerekmeyebilir - kontrol et
```

---

#### 8. Docker Runner Type Hints Ekleme
**Dosya:** `src/core/docker_runner.py`
**Sorun:** Fonksiyonlarda return type yok.

**Değişiklikler:**

```python
# Satır 18 - DEĞİŞTİR
def is_container_running() -> bool:  # ✅ Zaten var

# Satır 41 - DEĞİŞTİR
def get_docker_command(tool: str, args: List[str]) -> Tuple[str, List[str]]:  # ✅ Zaten var

# Satır 60 - DEĞİŞTİR
def run_command_sync(tool: str, args: List[str], timeout: int = 300) -> Tuple[int, str, str]:  # ✅ Zaten var

# Satır 90 - DEĞİŞTİR
def list_available_tools(force_refresh: bool = False) -> List[str]:  # ✅ Zaten var

# Satır 129 - DEĞİŞTİR
def invalidate_tools_cache():
# SONRASI:
def invalidate_tools_cache() -> None:

# Bu dosya neredeyse temiz, sadece son fonksiyon return type eksik
```

---

#### 9. Cleaner Type Hints Ekleme
**Dosya:** `src/core/cleaner.py`
**Sorun:** Fonksiyonlarda return type yok.

**Değişiklikler:**

```python
# Satır 39 - DEĞİŞTİR
def delete(self, file_path: str, secure: bool = True) -> bool:  # ✅ Zaten var

# Satır 73 - DEĞİŞTİR
def _is_safe_path(self, path: str) -> bool:  # ✅ Zaten var

# Satır 98 - EKLE
def _secure_overwrite(self, file_path: str):
# SONRASI:
def _secure_overwrite(self, file_path: str) -> None:

# Satır 113 - EKLE
def _privileged_delete(self, file_path: str) -> bool:  # ✅ Zaten var

# Satır 140 - EKLE
def cleanup_old_sessions(self, days: int = 7) -> int:  # ✅ Zaten var

# Bu dosya neredeyse temiz, sadece _secure_overwrite return type eksik
```

---

### 🟢 P2 - Orta (Önümüzdeki Sprint)

#### 10. Terminal View Log Metoduna Type Hint
**Dosya:** `src/ui/terminal_view.py`

```python
# Satır 276 - DEĞİŞTİR
def _log(self, text: str, color: str):
# SONRASI:
def _log(self, text: str, color: str) -> None:

# Satır 323 - DEĞİŞTİR
def _clear_output(self):
# SONRASI:
def _clear_output(self) -> None:

# Satır 327 - DEĞİŞTİR
def start_command(self, command: str, args: list, requires_root: bool = False):
# SONRASI:
def start_command(self, command: str, args: List[str], requires_root: bool = False) -> None:

# Satır 332-340 - DEĞİŞTİR
@staticmethod
def _escape(text: str) -> str:  # ✅ Zaten var
```

---

## ✅ TEST PROSEDÜRÜ

Her değişiklikten sonra:

### 1. UI Testleri
```bash
# Uygulamayı başlat
python main.py

# Kontroller:
# - Emoji yerine ASCII karakterler görünmeli ([TARGET], [AI], [OK] vb.)
# - Terminal'e uzun çıktı yapan komut çalıştır (örn: nmap localhost)
# - Buffer limiti çalışıyor mu kontrol et (10000+ satır)
# - Hatalı komut dene (örn: asdqweqwe123) - QProcess error mesajı görmeli
```

### 2. Core Modül Testleri
```bash
# Python shell'de test et
python
>>> from src.core.execution_manager import get_execution_manager
>>> mgr = get_execution_manager()
>>> print(mgr.mode)
ExecutionMode.NATIVE  # veya DOCKER
>>> # _time hatası olmamalı

>>> from src.core.cleaner import get_cleaner
>>> cleaner = get_cleaner()
>>> result = cleaner.delete("temp/test.txt")
>>> # Exception hatası olmamalı
```

### 3. Sprint 3 Validation
```bash
python src/tests/validate_sprint3.py
# Tüm testler geçmeli (8/8)
```

### 4. Type Hint Kontrolü (Opsiyonel)
```bash
pip install mypy
mypy src/core/process_manager.py --ignore-missing-imports
mypy src/core/execution_manager.py --ignore-missing-imports
# Hata olmamalı
```

---

## 📝 COMMIT MESAJLARI

Her düzeltme için ayrı commit at:

```bash
git add main.py
git commit -m "fix(ui): remove emoji characters for Windows compatibility

- Tüm emoji karakterler ASCII'ye çevrildi
- AGENT_RULES.md Madde 5.4 uyumu sağlandı
- Windows console encoding (cp1252) hatası önlendi
- Sprint 3 denetim raporu P0-3 maddesi"

git add src/core/process_manager.py
git commit -m "feat(core): add type hints and error handling to ProcessManager

- Tüm fonksiyonlara return type annotation eklendi
- QProcess.errorOccurred sinyali yakalanıyor
- Kullanıcıya anlamlı hata mesajları gösteriliyor
- Sprint 3 denetim raporu P0-2 ve P1-5 maddeleri"

git add src/core/execution_manager.py
git commit -m "refactor(core): improve ExecutionManager time handling

- Anti-pattern _time property kaldırıldı
- time modülü dosya başında import edildi
- Type hints iyileştirildi
- Sprint 3 denetim raporu P1-5 maddesi"

git add src/ui/terminal_view.py
git commit -m "feat(ui): add buffer limit to terminal output

- Maksimum 10000 satır limiti eklendi
- Aşıldığında ilk 1000 satır otomatik temizleniyor
- RAM tüketimi ve UI donması önlendi
- Sprint 3 denetim raporu P2-5 maddesi"

git add src/core/cleaner.py
git commit -m "refactor(core): improve exception handling in SecureCleaner

- Genel Exception yerine spesifik hatalar yakalanıyor
- OSError, IOError, PermissionError ayrı ayrı ele alınıyor
- Sprint 3 denetim raporu P1-1 maddesi"

git add src/core/validators.py src/core/docker_runner.py
git commit -m "docs(core): add missing return type hints

- validators.py ve docker_runner.py type hint kontrolü
- Eksik return type'lar eklendi
- Sprint 3 denetim raporu P0-1 maddesi"
```

---

## ⏱️ TAHMİNİ SÜRE

- P0 görevleri: **3-4 saat**
- P1 görevleri: **2-3 saat**
- P2 görevleri: **1 saat**
- Test: **1 saat**

**TOPLAM: ~7-9 saat (1 iş günü)**

---

## 🚨 DİKKAT EDİLECEKLER

1. **Emoji değişikliklerini UI'da test et:**
   - Her ekranda ASCII karakterler düzgün görünmeli
   - Tasarım bozulmamalı

2. **Buffer limiti çok agresif olabilir:**
   - 10000 satır yetersiz gelirse 20000 yap
   - Kullanıcı feedback'ine göre ayarla

3. **QProcess error handling kritik:**
   - Hatalı komutları test et (asdqwe123 gibi)
   - Docker kapalıyken dene
   - Yetki hataları dene (sudo gerektiren komut)

4. **Execution Manager değişikliği sonrası:**
   - Hem Docker hem Native modda test et
   - Cache çalışıyor mu kontrol et

5. **Type hints sonrası mypy test et (opsiyonel):**
   ```bash
   pip install mypy
   mypy src/core/ --ignore-missing-imports
   mypy src/ui/ --ignore-missing-imports
   ```

---

## 🔗 KEREM İLE KOORDİNASYON

Şu dosyalar her ikiniz tarafından değiştirilecek, merge conflict olabilir:

- `docker-compose.yml` - Kerem değiştiriyor (sen dokunma)
- `main.py` - Sen değiştiriyorsun (Kerem dokunmuyor)

Merge yaparken dikkatli ol, önce Kerem'in değişikliklerini pull et.

---

Başarılar! Sorularını Kerem ile koordine ederek çözebilirsin.
