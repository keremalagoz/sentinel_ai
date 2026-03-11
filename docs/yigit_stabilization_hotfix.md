# Yigit Stabilization Hotfix

**Tarih:** 7 Mart 2026  
**Kapsam:** Yiğit alanı (UI, system, security, process lifecycle, Windows native execution)

---

## Amaç

Bu hotfix turu, sprint planındaki orijinal structured command + process manager yaklaşımını Yiğit tarafında tekrar hizalamak için uygulandı. Ortak AI/registry semantiği yeniden tasarlanmadı; sadece Yiğit akışını kıran katmanlar düzeltildi.

---

## Tamamlanan Düzeltmeler

### 1. Backend-Owned Session Flow
- `src/ui/main_window.py` artık backend `session_id` değerini tek otorite olarak kullanır.
- `src/ui/chat_interface.py` chat history içinde `backend_session_id` metadata'sını saklar ve geri yükler.
- Yeni chat, mevcut chat ve restore edilmiş chat aynı backend session modeliyle çalışır.

### 2. Structured AI Command Execution
- AI tarafından önerilen komutlar artık tekrar flat string'e çevrilip `parse_command_with_risk()` üzerinden geçirilmez.
- Structured AI komutları `BackendGateway.prepare_structured_command()` ile doğrulanır.
- Raw terminal komutları için mevcut güvenlik kapısı korunur.

### 3. Typed Validation
- `src/core/validators.py` içinde structured arg validation ile raw command validation ayrıldı.
- URL query string, HTTP form payload ve percent-encoded değerler structured AI komut yolunda kabul edilir.
- Shell wrapper komutları (`bash -c`, `cmd /c`, `powershell -Command`) yalnızca structured AI path'te kontrollü şekilde doğrulanır.

### 4. Process Lifecycle
- `src/core/tools/base.py` içinde failed-to-start yarışı düzeltildi.
- Başlatılamayan process tek terminal sonuç üretir; ikinci bir timeout sonucu oluşturmaz.
- Windows tarafında `BaseTool` subprocess backend kullanır.

### 5. Windows Native Execution
- `src/core/platform_utils.py` içine merkezi executable resolution eklendi.
- `src/core/execution_manager.py` native path'te resolved executable kullanır.
- `src/core/process_manager.py` Windows native modda subprocess fallback ile çalışır.

---

## Test Sonuçları

7 Mart 2026 doğrulama koşuları:

- `pytest src/tests/test_ui_backend_boundary.py -q` -> 24 passed
- `pytest src/tests/test_sprint1_week2.py -q` -> 10 passed
- `pytest src/tests/test_ui_widgets.py -q` -> 144 passed
- `pytest src/tests/test_backend_chat_session.py -q` -> 2 passed
- `pytest src/tests/test_tool_commands.py -q` -> 112 passed
- `pytest src/tests/test_legacy_bridge.py -q` -> 19 passed
- Hedefli stabilizasyon paketi toplamı -> 311 passed
- Tam local run -> 1578 passed, 1 failed

Kalan tek kırık:

- `src/tests/test_action_planner_v2.py::test_intent_resolver`
- Bu test canlı LLM exact-match beklediği için oynak davranıyor ve Kerem handoff listesine alındı.

---

## Bilinçli Olarak Dışarıda Bırakılanlar

- `WEB_VULN_SCAN` intent semantiğinin uçtan uca yeniden tanımlanması
- Tool registry / AI sözleşmesinin geniş kapsamlı yeniden hizalanması
- Canlı LLM exact-match testlerinin ürün davranışı yerine deterministic stub/fallback ile yeniden tasarlanması

Bu başlıklar için bkz. `docs/kerem_handoff_issues.md`.
