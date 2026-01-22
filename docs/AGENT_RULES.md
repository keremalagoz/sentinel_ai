# SENTINEL AI - PROTOCOL & COMPLIANCE HANDBOOK

**Classification:** INTERNAL/RESTRICTED  
**Version:** 2.2-STRICT (Corporate Standard)  
**Enforcement:** MANDATORY  
**Single Source of Truth:** `docs/Detaylı Fazlandırılmış.pdf`

---

## 1. YÖNETİCİ ÖZETİ VE "VIBE CODING" FELSEFESİ

Bu doküman, Sentinel AI projesinde görev alan Yapay Zeka Asistanı (Agent) için bağlayıcı çalışma protokollerini tanımlar.

**Core Philosophy: "Vibe Coding"**

* **Kullanıcı (Developer):** Vizyonu belirler, akışı yönetir, yaratıcı kararları verir. Derin teknik detaylarda boğulmaz. "Vibe" odaklıdır.
* **Agent (Sen):** Mühendislik yükünü sırtlanır. Kod standartlarını, güvenlik protokollerini ve mimari bütünlüğü sessizce ve mükemmeliyetle uygular.
* **Sonuç:** Kullanıcı "bunu yap" dediğinde, Agent arka planda binlerce satırlık kuralları tarar ve "Production-Ready" kod üretir.

---

## 2. MİMARİ BÜTÜNLÜK VE ALTYAPI (INFRASTRUCTURE LOCK)

### 2.1. Konteynerizasyon İlkesi (The Docker Mandate)

Backend servisleri için "Lokalde çalışsın" teklifi kesinlikle yasaktır.

* **AI Engine:** Llama 3 servisi `docker/llama/Dockerfile` içinde yaşar.
* **API:** Orchestrator servisi `docker/api/Dockerfile` içinde yaşar.
* **Kural:** Agent, backend kodu yazarken daima konteyner bağlamını (volume paths, network aliases) kontrol etmek zorundadır.

### 2.2. Dosya Sistemi Otoritesi

`docs/Detaylı Fazlandırılmış.pdf` [Sayfa 1] içerisinde belirtilen hiyerarşi kutsaldır.

* **Yasak:** `/scripts`, `/bin`, `/utils` gibi tanımlanmamış klasörler oluşturulamaz.
* **Zorunlu:** İş mantığı `/src/core`, Arayüz `/src/ui`, Zeka `/src/ai` altında toplanır.

### 2.3. Teknoloji Stack Disiplini

`requirements.txt` dosyasındaki kütüphaneler projenin onaylı mühimmatıdır.

* **Onaylı:** `PyQt6`, `pydantic`, `openai`, `python-dotenv`, `defusedxml`.
* **Yasak:**
    * `tkinter` (Modern UI ihlali).
    * `subprocess.Popen` (Blocking call ihlali yerine `QProcess` kullan).
    * `requests` (Asenkron yapıya uygun değilse).
* **İstisna:** Yeni bir kütüphane gerekiyorsa, önce Kullanıcıdan (Lead Dev) onay alınmalıdır.

---

## 3. GİT VE SÜRÜM KONTROL PROTOKOLÜ (VCS GOVERNANCE)

Agent, Git reposunu bir cerrah titizliğiyle yönetmelidir.

### 3.1. Branch Stratejisi

Agent, şu an hangi branch üzerinde çalıştığını bağlamdan (context) anlamalıdır.

* **main:** NO-GO ZONE. Asla buraya kod önerilemez.
* **develop:** Entegrasyon sahası. Testleri geçen kodlar buraya adaydır.
* **dev_kerem:** Backend Sandbox. AI, Docker, Data Models.
* **dev_yigit:** Frontend Sandbox. UI, Qt Signals, Linux System.

### 3.2. Commit Mesajı Standartları (Auto-Compliance)

Kullanıcı "bunu commitle" dediğinde, Agent otomatik olarak Conventional Commits formatında mesaj hazırlar.

* `feat(ui): add dark mode toggle to terminal view`
* `fix(docker): resolve llama connection timeout in container`
* `refactor (core): optimize nmap xml parsing logic`
* `docs(sprint2): update orchestrator sequence diagrams`

---

## 4. ROLLER VE YETKİ MATRİSİ (CONTEXT AWARENESS)

Agent, komutu giren developer'ın kimliğine ("Persona") bürünerek yanıt vermelidir.

| Aktör | Odak Alanı | Yasaklı Bölge | Beklenen Çıktı Tipi |
| :--- | :--- | :--- | :--- |
| **KEREM** | AI, Backend, Data, Docker | CSS, Renk Paletleri, Widget Yerleşimi | JSON Şemaları, Pydantic Modelleri, API Endpointleri |
| **YİĞİT** | UI, UX, System, Security | Prompt Engineering, Model Tuning | PyQt Sinyalleri, `styles.py` güncellemeleri, Thread yönetimi |

**Senaryo:** Kerem "Terminal rengini değiştir" derse, Agent: *"Bu Yiğit'in alanına giriyor ancak `src/ui/styles.py` üzerinden şu değişikliği yapabiliriz..."* şeklinde profesyonelce yönlendirme yapar.

---

## 5. KOD KALİTESİ VE MÜHENDİSLİK STANDARTLARI

Kod "çalışıyor" demek, "bitti" demek değildir.

### 5.1. Tip Güvenliği (Type Safety)

Python'ın esnekliği, kurumsal projede zafiyettir. %100 Type Hinting zorunludur.

* **Hatalı:** `def parse(data):`
* **Doğru:** `def parse(data: str) -> list [StandardFinding]:`

### 5.2. Asenkron UI Koruması (Non-Blocking UI)

PyQt arayüzünü dondurmak Ağır Suçtur.

* Uzun süren her işlem (AI request, Nmap scan) kesinlikle `QThread` veya `QProcess` içinde yapılmalıdır.
* Kullanıcıya daima "Loading..." veya "Processing..." geri bildirimi verilmelidir.

### 5.3. Hata Yönetimi (Fail-Safe Architecture)

* Uygulama çökmemeli (Crash-Free).
* `try-except` blokları spesifik olmalı (`except Exception:` yasak).
* Yetki hataları (Exit Code 126/127) yakalanmalı ve UI tarafında "Yetki Reddedildi" uyarısı ile gösterilmelidir.

### 5.4. Emoji Yasağı (No Emoji Policy)

**Hiçbir script veya kaynak kod dosyasında emoji karakterleri kullanılamaz.**

* **Sebep:** Windows console encoding (cp1254/cp1252) emoji karakterlerini desteklemez ve `UnicodeEncodeError` hatalarına yol açar.
* **Alternatif:** Durum belirtmek için ASCII karakter kombinasyonları kullanılmalıdır:
    * `[OK]` yerine "OK" etiketi
    * `[ERROR]` yerine "ERROR" etiketi
    * `[WARNING]` yerine "WARNING" etiketi
    * `[INFO]` yerine "INFO" etiketi
    * `[BLOCKED]` yerine "BLOCKED" etiketi
* **Kapsam:** `.py`, `.sh`, `.md` (kod blokları dahil) ve tüm kaynak dosyaları.

---

## 6. GÜVENLİK PROTOKOLLERİ (SEC-OPS)

### 6.1. Root Yetki Yönetimi

* Kod içinde asla hardcoded sudo şifresi bulunamaz.
* Yetki yükseltme sadece `pkexec` wrapper ile yapılmalıdır (`src/core/process_manager.py`).

### 6.2. Veri Gizliliği (Data Masking)

* Cloud AI (OpenAI) servisine gönderilen verilerde IP adresleri ve Kurumsal Domainler maskelenmelidir `([HOST_X])`.
* Bu maskeleme işlemi `src/ai/masking.py` modülünde merkezi olarak yönetilmelidir.

---

## 7. SPRINT UYGULAMA KURALLARI

Agent, zaman yolcusu değildir. Mevcut Sprint dışındaki özellikler önerilemez.

1.  **Mevcut Durum Analizi:** `son_durum.md` dosyasını oku.
2.  **Hedef:** Sadece aktif Sprint maddelerine odaklan.
3.  **Definition of Done:** Kodun bittiğini iddia etmeden önce, PDF dokümanındaki "Başarı Kriterleri"ni kontrol et ve kullanıcıya raporla.

**YASAL UYARI:** Bu protokollerin ihlali, projenin mimari bütünlüğünü bozacağı için Agent tarafından reddedilmeli ve düzeltici eylem önerilmelidir.
