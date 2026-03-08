# AI Directive - Sprint 3.5 v2

Bu dosya, yeni bir sohbette Sprint 3.5 v2 calismasina dogrudan devam edebilmek icin hazirlanmis resmi aktarim belgesidir.

## 1. Calisma Amaci

Sprint 3.5 v2 hedefi su sekilde sabitlenmistir:

- AI ve action planner mimarisi `dev_kerem` cizgisinde korunacak.
- `develop` branch'indeki execution-first / metadata-only registry mimarisi ana yapi yapilmayacak.
- UI tarafinda `develop` branch'indeki degisikliklerin tamami alinacak.
- Tool katmani secici ve planner-uyumlu sekilde `dev_kerem` yapisina adapte edilerek alinacak.
- Is bitince degisiklikler `dev_kerem` uzerinden `develop` branch'ine merge edilecek.

Bu gecis paketi artik `Sprint 3.5 v2` ismiyle anilmaktadir.

## 2. Mimari Karar

Hedef mimari su formuldedir:

- develop UI
- dev_kerem AI/planner
- secici develop tools

Acik olarak alinmayacak seyler:

- metadata-only `build_tool_spec()` davranisinin planner cekirdegine dogrudan tasinmasi
- execution-first orchestrator modelinin ana akis haline gelmesi
- heuristic agir secondary command uretimi
- dynamic risk inference'in ana guvenlik modeli haline gelmesi

Korunacak ana AI/planner dosyalari:

- `src/ai/command_builder.py`
- `src/ai/orchestrator.py`
- `src/ai/tool_registry.py`

Tool katmaninda referans alinacak dosyalar:

- `src/core/tools/base.py`
- `src/core/tool_base.py`
- `src/core/tools/`

UI tarafinda hedef parity dosyalari:

- `src/ui/main_window.py`
- `src/ui/chat_interface.py`
- `src/ui/terminal_view.py`
- `src/ui/settings_dialog.py`
- `src/ui/i18n.py`
- `src/ui/styles.py`

## 3. Branch Stratejisi

Karar su sekildedir:

1. `experimental` branch'i, mevcut `develop` mimarisini kaybetmemek icin olusturuldu.
2. Ayrica feature/work branch acilmiyor.
3. Tum gercek gelistirme dogrudan `dev_kerem` branch'i uzerinde yuruyor.
4. Is tamamlandiginda `dev_kerem` -> `develop` merge yapilacak.

Mevcut git durumu:

- aktif branch: `dev_kerem`
- yedek branch: `experimental`
- stash: `stash@{0}: On develop: temp sqlite runtime artifacts before sprint35v2`

Not:

- Bu stash, branch gecisi sirasinda olusan SQLite runtime `-wal/-shm` artefact'larini korumak icin alindi.
- Kod calismasina ait mantiksal bir degisiklik degil.

## 4. Roadmap Kaydi

Takip belgesi guncellendi:

- `docs/sprint_roadmap.md`

Bu dosyada `Sprint 3.5 v2` bolumu eklendi ve asagidaki gorevler tanimlandi:

- `3.5v2.1` Experimental guvenlik dali
- `3.5v2.2` Ilk guvenlik/telemetry dilimi
- `3.5v2.3` Terminal risk yuzeyi
- `3.5v2.4` UI parity gocusu
- `3.5v2.5` Faz 1 tool gocusu
- `3.5v2.6` Planner-friendly registry uyarlamasi
- `3.5v2.7` Faz 2 tool politikasi
- `3.5v2.8` Regresyon ve merge hazirligi

Guncel durum:

- `3.5v2.1` tamamlandi
- `3.5v2.2` tamamlandi
- `3.5v2.3` tamamlandi
- `3.5v2.4` kismen ilerledi, bitmedi

## 5. Simdiye Kadar Yapilanlar

### 5.1 Branch ve Guvenlik Hazirligi

Tamamlandi:

- `experimental` branch olusturuldu.
- Calisma `dev_kerem` branch'ine cekildi.
- SQLite runtime artefact'lari stash'e alindi.

### 5.2 Ilk Guvenlik / Telemetry Dilimi

Asagidaki dosyalarda uygulandi:

- `src/application/backend_gateway.py`
- `src/core/cleaner.py`
- `src/ui/main_window.py`
- `src/ui/settings_dialog.py`
- `src/ui/i18n.py`

Yapilanlar:

- `secure_delete` ayari backend facade uzerinden yonetilir hale getirildi.
- `cleanup_old_sessions()` secure-delete flag kabul edecek sekilde genisletildi.
- `SecuritySettingsDialog` icine guvenlik politikasi alani eklendi:
  - `confirm_root`
  - `warn_high_risk`
  - `auto_cleanup`
- `MainWindow` bu ayarlari yukleyip kaydeder hale getirildi.
- Onay akisi sadece root'a degil, medium/high risk seviyelerine de ayar tabanli baglandi.
- Status bar'a runtime telemetry etiketi eklendi.
- Yeni i18n anahtarlari eklendi.

### 5.3 i18n Dayaniklilik Iyilestirmesi

Dosya:

- `src/ui/i18n.py`

Yapilan ek yapisal iyilestirme:

- Tum ceviri sozlukleri English base ile otomatik tamamlanir hale getirildi.
- Boylece yeni anahtar eklendiginde diger diller tek tek eksik key nedeniyle kirilmiyor.

### 5.4 Terminal Risk Yuzeyi

Dosya:

- `src/ui/terminal_view.py`

Yapilanlar:

- develop tarzinda renkli risk banner yapisi eklendi.
- Terminal session icinde `risk_level` state tutuluyor.
- Komut baslangicinda duz `[RISK]` yazisi yerine gorsel risk banner basiliyor.
- Komut bitince / durdurulunca / auth fail durumunda risk state sifirlaniyor.

### 5.5 Backend Session UI Parity Baslangici

Dosyalar:

- `src/ui/main_window.py`
- `src/ui/i18n.py`

Yapilanlar:

- `MainWindow` artik backend orchestrator conversation session id'si olusturup sakliyor.
- `Yeni Sohbet` ile backend session yenileniyor.
- Kullanici mesajlari backend'e local chat id yerine gercek backend session id ile gidiyor.
- Status bar'a session gostergesi eklendi.

## 6. Dogrulama Durumu

Simdiye kadar kosulan ve gecen testler:

- `src/tests/test_chat_history_cleanup_regression.py`
- `src/tests/test_i18n.py`
- `src/tests/test_ui_features.py`

Guncel bilinen sonuc:

- `test_chat_history_cleanup_regression.py`: gecti
- `test_i18n.py`: gecti
- `test_ui_features.py`: gecti
- son birlikte kosuda: `362 passed`

Ayrica dokunulan dosyalarda editor hata taramasi temizdi.

## 7. Henuz Yapilmayanlar

### 7.1 Kalan UI Parity Isi (`3.5v2.4`)

Hala tamamlanmamis UI parity calismalari var.

Odak dosyalar:

- `src/ui/chat_interface.py`
- `src/ui/main_window.py`
- gerekirse `src/ui/settings_dialog.py`
- gerekirse `src/ui/styles.py`

Beklenen devam isleri:

- Chat/session davranisinin develop parity acisindan eksik kalan kisimlarini gozden gecirmek
- Header / status / UI akislarindaki kalan parity farklarini kapatmak
- UI smoke ve mevcut testlerle dogrulamak

### 7.2 Faz 1 Tool Gocusu (`3.5v2.5`)

Bu, UI parity sonrasindaki bir sonraki ana fazdir.

Oncelikli alinmasi onerilen tool'lar:

- `whois_lookup`
- `nmap_os_detection`
- mevcut recon ve scan tool'larindaki guvenli `build_command()` iyilestirmeleri

Ilgili dosyalar:

- `src/core/tool_base.py`
- `src/core/tools/base.py`
- `src/core/tools/`
- `src/core/sentinel_coordinator.py`

### 7.3 Planner-Friendly Registry Uyarlamasi (`3.5v2.6`)

Bu faz kritik ama henuz baslanmadi.

Ana prensip:

- `dev_kerem` planner kontrati korunacak
- `tool_registry.py` yeni tool'lari anlayacak sekilde genisletilecek
- ancak metadata-only registry mantigi ana akis yapilmayacak

Ana dosya:

- `src/ai/tool_registry.py`

### 7.4 Faz 2 Tool Politikasi (`3.5v2.7`)

Zengin parametre isteyen tool'lar bilincli sekilde ikinci faza birakildi:

- `src/core/tools/hydra_http.py`
- `src/core/tools/hydra_ssh.py`
- `src/core/tools/sqlmap_scan.py`

Sebep:

- `hydra_http` icin `form_path`, `form_params`, `fail_string` gibi alanlar gerekiyor
- `hydra_ssh` icin `username`, `wordlist` gerekiyor
- `sqlmap` icin `level`, `risk`, `forms`, `dbs` gibi typed alanlar gerekiyor

Bu tool'lar icin ya explicit clarification politikasi yazilacak ya da daha sonra planner uyumlu sekilde acilacak.

## 8. Kritik Kurallar

Yeni sohbette bu kurallar korunmali:

1. AI/planner tarafini develop mimarisine cevirme.
2. `dev_kerem` action planner mantigini koru.
3. UI parity calisirken planner kontratini bozma.
4. Tool gocusu UI parity tamamlanmadan ana odak haline gelmesin.
5. Her dilimden sonra hedefli test kos.
6. Yol haritasi dosyasi `docs/sprint_roadmap.md` guncel tutulmaya devam edilmeli.

## 9. Bir Sonraki Mantikli Adim

Yeni sohbette ilk is olarak su yapilmali:

1. `3.5v2.4` kalan UI parity farklari icin `chat_interface.py` ve `main_window.py` uzerinde odakli inceleme yap.
2. Parity eksiklerini kucuk ve testlenebilir bir dilim halinde uygula.
3. `src/tests/test_ui_features.py` ve gerekirse `src/tests/test_i18n.py` ile tekrar dogrula.
4. UI parity yeterince oturdugunda `3.5v2.5` Faz 1 tool gocusune gec.

## 10. Handoff Ozeti

Yeni sohbette bunu baz al:

- Branch: `dev_kerem`
- Yedek branch: `experimental`
- Hedef sprint: `Sprint 3.5 v2`
- Durum: UI parity devam ediyor
- Tamamlananlar: `3.5v2.1`, `3.5v2.2`, `3.5v2.3`
- Siradaki aktif is: `3.5v2.4`

Bu belge, yeni sohbette ayni baglamla devam etmek icin yeterli resmi durum ozeti olarak kullanilmalidir.