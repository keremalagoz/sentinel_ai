# Sprint 3.6 — Backend Agent-Chat Foundation (UI Değişikliği Yok)

**Tarih:** 4 Mart 2026  
**Durum:** Tamamlandı ✅  
**Ön Koşul:** Action Planner v2.1 + Sprint 3.3 altyapısı

---

## 1) Hedef

Mevcut Action Planner v2.1 mimarisini bozmadan, sadece backend katmanında
session-aware çok turlu sohbet altyapısı eklemek.

Kısıtlar:
- UI tarafına değişiklik yok
- Mevcut deterministik intent→tool→command akışı korunacak
- Varsayılan davranış yarı-otomatik olacak (öneri + onay)

---

## 2) Teslimatlar

| # | Teslimat | Dosya(lar) | Durum |
|---|----------|------------|-------|
| 3.6.1 | Kalıcı conversation memory store | `src/core/conversation_memory.py` | ✅ |
| 3.6.2 | Session-aware orchestrator | `src/ai/orchestrator.py` | ✅ |
| 3.6.3 | Agentik yanıt metadata'sı | `src/ai/orchestrator.py` | ✅ |
| 3.6.4 | Chat REST endpointleri | `src/application/api_server.py` | ✅ |
| 3.6.5 | Gateway session çağrısı | `src/application/backend_gateway.py` | ✅ |
| 3.6.6 | Backend testleri | `src/tests/test_backend_chat_session.py` | ✅ |

---

## 3) Teknik Değişiklik Özeti

### 3.1 Conversation Memory (SQLite)

Yeni tablolar:
- `conversation_sessions`
- `conversation_turns`

Amaç:
- session lifecycle yönetimi
- turn bazlı user/assistant geçmişi
- orchestrator için context render

### 3.2 Orchestrator Genişlemesi

`process_v2(...)` imzası genişletildi:
- `session_id`
- `memory_turn_limit`

Yeni davranış:
- Session varsa son turlar bağlama eklenir
- Çıktıya `requires_approval` eklenir
- Çıktıya `agent_observation` eklenir

### 3.3 API Uçları

- `POST /api/chat/session`
- `POST /api/chat/turn`
- `GET /api/chat/history/{session_id}`

Bu uçlar UI değişikliği gerektirmeden backend chatbot davranışı sağlar.

---

## 4) Doğrulama

Çalıştırılan testler:
- `pytest src/tests/test_backend_chat_session.py -q` → **2 passed**
- `pytest src/tests/test_ui_backend_boundary.py -q` → **19 passed**

Toplam hedefli doğrulama: **21 passed**

---

## 5) Risk / Notlar

- FastAPI `on_event` deprecation warning'i mevcut (işlevsel blokaj değil).
- Full suite bu sprintte uçtan uca yeniden koşturulmadı; en son bilinen full sonuç 242 passed.

---

## 6) Sprint 4'e Etkisi

Sprint 4 (Veri Adaptasyonu) planı korunur.
Sprint 3.6 ile gelen session-memory/chat API katmanı Sprint 4 ile çakışmaz,
aksine structured result çıktılarının çok turlu akışa taşınmasını kolaylaştırır.
