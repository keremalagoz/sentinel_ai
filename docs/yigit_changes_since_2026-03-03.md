# Yiğit Teknik Değişim Raporu

Bu doküman, 03.03.2026 tarihinde Kerem kaynaklı güncel durumu aldıktan sonra 07.03.2026 tarihine kadar Yiğit tarafından yapılan teknik değişiklikleri Kerem'in hızlı ve doğru şekilde görebilmesi için hazırlanmıştır.

Kapsam:
- Kaynak: `git log`, commit istatistikleri, mevcut çalışma ağacı
- Aralık: 03.03.2026 00:00 (+0300) -> 07.03.2026
- Amaç: "Yiğit bu aralıkta teknik olarak ne yaptı, nerelere dokundu, mimari olarak neyi değiştirdi, neyi güçlendirdi?" sorusuna net cevap vermek

## 1. Kısa Özet

Bu aralıkta Yiğit tarafında yapılan işler dört ana eksende toplandı:

1. Sprint 3 kapanışında AI-security entegrasyonu, root confirmation, risk göstergeleri ve cleanup/regression hattı kuruldu.
2. UI tarafında i18n sistemi, settings dialog iyileştirmeleri, layout/font düzeltmeleri ve geniş UI test kapsamı eklendi.
3. Sprint 3.5 hotfix turunda komut üretim hattının doğruluğu artırıldı, benchmark/test altyapısı kuruldu ve yeni tool seti eklendi.
4. Sprint 3.5 sonrası accuracy turunda intent parsing ve prompt-to-command hattı daha toleranslı ve daha deterministik hale getirildi.

Bunlara ek olarak, bugün mevcut çalışma ağacında henüz commitlenmemiş bir Yiğit-first stabilizasyon turu da bulunuyor. Bu turda UI/backend session ownership, structured AI command execution, typed validation ve Windows native execution sorunları düzeltilmiş durumda.

## 2. Kronolojik Değişim Akışı

### 03.03.2026 - Sprint 3 kapanış ve AI-security entegrasyonu

Commit:
- `c078f8d0` - `Sprint 3 close: AI-security integration, root confirmation, risk indicators, cleanup hardening, regression tests`

Öne çıkan teknik işler:
- [src/application/backend_gateway.py](/Users/Yigit/Desktop/sentinel_root/src/application/backend_gateway.py) içinde UI ile backend arasındaki command/risk köprüsü güçlendirildi.
- [src/ui/main_window.py](/Users/Yigit/Desktop/sentinel_root/src/ui/main_window.py) ve [src/ui/chat_interface.py](/Users/Yigit/Desktop/sentinel_root/src/ui/chat_interface.py) tarafında AI güvenlik onayı ve kullanıcı akışı yenilendi.
- [src/ui/terminal_view.py](/Users/Yigit/Desktop/sentinel_root/src/ui/terminal_view.py) üzerinde terminal davranışı ve görsel bütünlük revize edildi.
- [src/core/cleaner.py](/Users/Yigit/Desktop/sentinel_root/src/core/cleaner.py) içinde cleanup sertleştirildi.
- [src/core/process_manager.py](/Users/Yigit/Desktop/sentinel_root/src/core/process_manager.py) tarafında process yaşam döngüsü elden geçirildi.
- Yeni regresyon dokümanı ve testleri eklendi:
  - [docs/ui_regression_checklist.md](/Users/Yigit/Desktop/sentinel_root/docs/ui_regression_checklist.md)
  - [src/tests/test_chat_history_cleanup_regression.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_chat_history_cleanup_regression.py)
  - [src/tests/test_ui_backend_boundary.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_ui_backend_boundary.py)

Etki:
- AI tarafından önerilen komutların risk seviyesinin kullanıcıya görünür olması sağlandı.
- Root gerektiren komutların doğrudan akması yerine kontrollü onay akışı geldi.
- UI ve terminal tarafındaki güvenlik/süreç köprüsü Sprint 3 sonu için üretim kalitesine yaklaştırıldı.

İstatistik:
- 12 dosya değişti
- 1027 ekleme, 360 silme

### 04.03.2026 - i18n sistemi, UI entegrasyonu ve performans/test turu

Commitler:
- `f8af8429` - `feat(ui): add i18n system with 11 languages and settings dialog`
- `78765db8` - `feat(ui): integrate i18n, layout swap, and font fixes across UI components`
- `73586845` - `fix(ai): add i18n command message translation and pre-compile regex`
- `6da30d10` - `perf(core): pre-compile regex patterns in validators and parser_framework`
- `93bfef45` - `test(ui): add comprehensive UI, i18n, and optimization test suites (591 tests)`
- `e04b5802` - `docs(sprint3.4): update all documentation for Sprint 3.4 completion`

Öne çıkan teknik işler:
- [src/ui/i18n.py](/Users/Yigit/Desktop/sentinel_root/src/ui/i18n.py) eklendi ve 11 dil desteği getirildi.
- [src/ui/settings_dialog.py](/Users/Yigit/Desktop/sentinel_root/src/ui/settings_dialog.py), [src/ui/styles.py](/Users/Yigit/Desktop/sentinel_root/src/ui/styles.py), [src/ui/main_window.py](/Users/Yigit/Desktop/sentinel_root/src/ui/main_window.py), [src/ui/chat_interface.py](/Users/Yigit/Desktop/sentinel_root/src/ui/chat_interface.py), [src/ui/terminal_view.py](/Users/Yigit/Desktop/sentinel_root/src/ui/terminal_view.py) boyunca i18n entegrasyonu tamamlandı.
- Font fallback, layout swap ve bileşen düzeyi görsel tutarlılık sorunları giderildi.
- [src/ai/intent_resolver.py](/Users/Yigit/Desktop/sentinel_root/src/ai/intent_resolver.py), [src/ai/hierarchical_resolver.py](/Users/Yigit/Desktop/sentinel_root/src/ai/hierarchical_resolver.py), [src/ai/orchestrator.py](/Users/Yigit/Desktop/sentinel_root/src/ai/orchestrator.py) tarafında AI mesajları için çeviri/uyum düzeltmeleri yapıldı.
- [src/core/validators.py](/Users/Yigit/Desktop/sentinel_root/src/core/validators.py) ve [src/core/parser_framework.py](/Users/Yigit/Desktop/sentinel_root/src/core/parser_framework.py) içinde regex precompile ile küçük ama sistematik performans iyileştirmesi yapıldı.
- Büyük UI/test kapsamı eklendi:
  - [src/tests/test_i18n.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_i18n.py)
  - [src/tests/test_ui_features.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_ui_features.py)
  - [src/tests/test_ui_widgets.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_ui_widgets.py)
  - [src/tests/test_optimizations.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_optimizations.py)

Etki:
- UI artık yalnızca İngilizce çalışan bir prototip değil, ayarlanabilir ve uluslararasılaştırılmış bir arayüz oldu.
- Görsel akış ve kullanıcı deneyimi tutarlılığı arttı.
- Test kapsamı ciddi şekilde büyüdü; UI regressions daha erken yakalanabilir hale geldi.

### 05.03.2026 - Sprint 3.5 hotfix ve komut üretim doğruluğu turu

Commit:
- `9dcec812` - `feat(sprint3.5): hotfix - security confirmation, keyword fallback, accuracy benchmark, docs sync`
- Ardından merge: `7421e12e`

Öne çıkan teknik işler:
- Security settings persistence düzeltildi:
  - `confirm_root`
  - `warn_high_risk`
  - `auto_cleanup`
- [src/ai/orchestrator.py](/Users/Yigit/Desktop/sentinel_root/src/ai/orchestrator.py) içinde keyword fallback eklendi; LLM parse başarısız olduğunda tüm akışın boşa düşmesi azaltıldı.
- Komut üretim kalitesi ölçülür hale getirildi:
  - [scripts/auto_benchmark.py](/Users/Yigit/Desktop/sentinel_root/scripts/auto_benchmark.py)
  - [scripts/pipeline_accuracy_test.py](/Users/Yigit/Desktop/sentinel_root/scripts/pipeline_accuracy_test.py)
  - [src/tests/test_command_accuracy.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_command_accuracy.py)
  - [src/tests/test_pipeline_integration.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_pipeline_integration.py)
- Tool seti genişletildi:
  - [src/core/tools/nmap_os_detection.py](/Users/Yigit/Desktop/sentinel_root/src/core/tools/nmap_os_detection.py)
  - [src/core/tools/whois_lookup.py](/Users/Yigit/Desktop/sentinel_root/src/core/tools/whois_lookup.py)
  - [src/core/tools/hydra_ssh.py](/Users/Yigit/Desktop/sentinel_root/src/core/tools/hydra_ssh.py)
  - [src/core/tools/hydra_http.py](/Users/Yigit/Desktop/sentinel_root/src/core/tools/hydra_http.py)
  - [src/core/tools/sqlmap_scan.py](/Users/Yigit/Desktop/sentinel_root/src/core/tools/sqlmap_scan.py)
- Tool registry ve AI katmanı yeni araçları destekleyecek şekilde büyütüldü:
  - [src/ai/tool_registry.py](/Users/Yigit/Desktop/sentinel_root/src/ai/tool_registry.py)
  - [src/ai/intent_resolver.py](/Users/Yigit/Desktop/sentinel_root/src/ai/intent_resolver.py)
  - [src/ai/hierarchical_resolver.py](/Users/Yigit/Desktop/sentinel_root/src/ai/hierarchical_resolver.py)
  - [src/ai/keyword_filter.py](/Users/Yigit/Desktop/sentinel_root/src/ai/keyword_filter.py)
- Audit ve doğrulama testleri çok genişletildi:
  - [src/tests/test_sprint35_audit.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_sprint35_audit.py)
  - [src/tests/test_tool_commands.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_tool_commands.py)
  - [src/tests/test_new_tools.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_new_tools.py)

Etki:
- Komut üretim hattı ilk kez ölçülebilir benchmark mantığına kavuştu.
- LLM'in hata verdiği veya eksik parse ettiği durumlarda sistem tamamen düşmek yerine fallback ile komut üretebilir hale geldi.
- Ürün yüzeyi ciddi şekilde büyüdü; özellikle reconnaissance ve web/auth odaklı yeni araçlar eklendi.

İstatistik:
- 64 dosya değişti
- 7836 ekleme, 207 silme
- Commit mesajına göre test sonucu: `1451 passed`

### 06.03.2026 - Accuracy %100 turu ve parser dayanıklılığı

Commitler:
- `a8e15998` - `fix(ai): Implement 100% pipeline accuracy with DNS hard-override, JSON tolerance, and target regex tweaks`
- `05778d29` - `docs: Update son_durum.md with 100% Sprint 3.5 pipeline accuracy completion status`

Öne çıkan teknik işler:
- [src/ai/intent_resolver.py](/Users/Yigit/Desktop/sentinel_root/src/ai/intent_resolver.py) tarafında JSON toleransı artırıldı.
- [src/ai/orchestrator.py](/Users/Yigit/Desktop/sentinel_root/src/ai/orchestrator.py) içinde prompt-to-command dayanıklılığı artırıldı.
- DNS intentleri için hard override mantığı eklendi.
- Target extraction regexleri rafine edildi.
- Legacy ve prompt coverage testleri eklendi:
  - [src/tests/test_legacy_bridge.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_legacy_bridge.py)
  - [src/tests/test_prompt_to_command.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_prompt_to_command.py)
  - [src/tests/test_intent_prompt_coverage.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_intent_prompt_coverage.py)
  - [src/tests/test_hierarchical_resolver.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_hierarchical_resolver.py)
- Benchmark tarafı derinleştirildi:
  - [scripts/complex_prompt_command_benchmark.py](/Users/Yigit/Desktop/sentinel_root/scripts/complex_prompt_command_benchmark.py)

Etki:
- Serbest kullanici promptundan nihai komuta giden zincir daha deterministik hale geldi.
- JSON truncation, toleranssız parse ve hedef çıkarım hataları azaltıldı.
- Sistem yalnızca "çalışıyor" seviyesinde değil, "accuracy-driven" iterasyon seviyesine taşındı.

İstatistik:
- 29 dosya değişti
- 2746 ekleme, 124 silme

### 07.03.2026 - Intent JSON mode zorlaması

Commit:
- `63507a7b` - `fix(ai): enforce JSON mode for intent resolution to prevent truncation`

Öne çıkan teknik iş:
- [src/ai/intent_resolver.py](/Users/Yigit/Desktop/sentinel_root/src/ai/intent_resolver.py) içinde intent çözümleme sırasında JSON mode daha katı hale getirildi.

Etki:
- Özellikle uzun veya değişken LLM çıktılarında kırpılma/truncation ihtimali daha da azaltıldı.

## 3. Yiğit'in Dokunduğu Ana Teknik Alanlar

### UI ve kullanıcı akışı

Ana dosyalar:
- [src/ui/main_window.py](/Users/Yigit/Desktop/sentinel_root/src/ui/main_window.py)
- [src/ui/chat_interface.py](/Users/Yigit/Desktop/sentinel_root/src/ui/chat_interface.py)
- [src/ui/terminal_view.py](/Users/Yigit/Desktop/sentinel_root/src/ui/terminal_view.py)
- [src/ui/settings_dialog.py](/Users/Yigit/Desktop/sentinel_root/src/ui/settings_dialog.py)
- [src/ui/styles.py](/Users/Yigit/Desktop/sentinel_root/src/ui/styles.py)
- [src/ui/i18n.py](/Users/Yigit/Desktop/sentinel_root/src/ui/i18n.py)

Buradaki katkı tipi:
- güvenlik onayı akışının UI'ya taşınması
- risk görünürlüğü
- i18n ve ayar ekranı
- layout/font stabilizasyonu
- chat/terminal bütünlüğü

### AI -> komut üretim hattı

Ana dosyalar:
- [src/ai/orchestrator.py](/Users/Yigit/Desktop/sentinel_root/src/ai/orchestrator.py)
- [src/ai/intent_resolver.py](/Users/Yigit/Desktop/sentinel_root/src/ai/intent_resolver.py)
- [src/ai/hierarchical_resolver.py](/Users/Yigit/Desktop/sentinel_root/src/ai/hierarchical_resolver.py)
- [src/ai/keyword_filter.py](/Users/Yigit/Desktop/sentinel_root/src/ai/keyword_filter.py)
- [src/ai/tool_registry.py](/Users/Yigit/Desktop/sentinel_root/src/ai/tool_registry.py)

Buradaki katkı tipi:
- keyword fallback
- JSON tolerance / JSON mode sıkılaştırma
- target regex iyileştirmeleri
- yeni tool intentleri
- benchmark ve doğruluk odaklı testleme

### Core ve execution katmanı

Ana dosyalar:
- [src/application/backend_gateway.py](/Users/Yigit/Desktop/sentinel_root/src/application/backend_gateway.py)
- [src/core/process_manager.py](/Users/Yigit/Desktop/sentinel_root/src/core/process_manager.py)
- [src/core/validators.py](/Users/Yigit/Desktop/sentinel_root/src/core/validators.py)
- [src/core/parser_framework.py](/Users/Yigit/Desktop/sentinel_root/src/core/parser_framework.py)
- [src/core/tools/base.py](/Users/Yigit/Desktop/sentinel_root/src/core/tools/base.py)

Buradaki katkı tipi:
- command gate
- validation
- process yaşam döngüsü
- tool execution standardizasyonu

### Test ve kalite altyapısı

Yiğit bu aralıkta test yüzeyini ciddi biçimde büyüttü. Özellikle şu alanlarda:
- UI regresyonları
- i18n ve widget davranışları
- tool command doğruluğu
- pipeline integration
- prompt-to-command benchmark
- legacy bridge uyumu
- sprint audit testleri

Bu değişim, projenin "özellik geliştirme" modundan "ölçülebilir doğruluk ve regresyon kontrolü" moduna geçişinde kritik rol oynadı.

## 4. Komut Üretim Mimarisinde Ne Değişti?

Bu bölüm özellikle Kerem'in görmek isteyeceği mimari farkı özetler.

### 03.03.2026 civarındaki yapı

Yaklaşık akış:

`kullanıcı girdisi -> intent çözümleme -> tool/command seçimi -> string komut -> UI/backend gate -> execution`

Bu modelin özellikleri:
- AI çıktısı ile manuel yazılan komut arasında ayrım zayıftı.
- Hattın ana taşıma biçimi çoğunlukla string komuttu.
- Hata olduğunda fallback ve doğrulama daha sınırlıydı.
- Komut üretim kalitesi ölçülüyor olsa bile sistematik benchmark yoğun değildi.

### 07.03.2026 itibarıyla oluşan yapı

Yaklaşık akış:

`kullanıcı girdisi -> intent çözümleme -> fallback/override/tolerance katmanı -> tool registry -> structured command mantığı -> UI onayı/risk -> execution`

Bu turda Yiğit'in etkisiyle gelen değişimler:
- intent çözümlemede JSON toleransı artırıldı
- keyword fallback eklendi
- DNS gibi alanlarda hard override mantığı getirildi
- target extraction regexleri iyileştirildi
- prompt-to-command akışı benchmark ve audit testleriyle sürekli ölçülür hale geldi
- tool seti ve registry yüzeyi genişletildi

### Kazanımlar

Eskisine göre kazanımlar:
- LLM parse hatası olduğunda tüm zincir kopmuyor, fallback devreye girebiliyor.
- Komut üretim doğruluğu rastlantısal izlenim yerine test/benchmark ile gözlenebiliyor.
- Intent -> command eşleşmesi daha deterministik hale geliyor.
- Yeni araçlar için ölçeklenebilir bir registry/test yapısı oluşuyor.
- Doğruluk iyileştirmeleri dokümantasyona ve benchmark scriptlerine bağlanmış durumda.

### Sınırlar

Bu aralıkta büyüyen bazı ortak alanlar daha sonra sözleşme drift'i de üretti:
- registry'nin desteklediği bazı komutlar UI gate tarafından aynı genişlikte çalıştırılmıyordu
- structured AI command ile raw string command ayrımı tam netleşmemişti
- bazı doğrulama kuralları tool-aware değil, global regex tabanlı kalmıştı

Bu konuların Yiğit tarafını etkileyen kısmı mevcut çalışma ağacında ayrıca stabilize edildi; ayrıntısı aşağıdaki bölümde.

## 5. Bugün Çalışma Ağacında Olan, Henüz Commitlenmemiş Yiğit Düzeltmeleri

Bu bölüm git geçmişinde henüz commit olarak yer almayan ama şu anda çalışma ağacında bulunan Yiğit-first stabilizasyon işlerini anlatır.

### Session ownership düzeltmesi

Dosyalar:
- [src/ui/main_window.py](/Users/Yigit/Desktop/sentinel_root/src/ui/main_window.py)
- [src/ui/chat_interface.py](/Users/Yigit/Desktop/sentinel_root/src/ui/chat_interface.py)

Yapılan iş:
- backend `session_id` tek otorite olacak şekilde UI akışı düzeltildi
- UI history/chat id ile backend conversation id ayrıştırıldı
- restore/new chat akışında session continuity güçlendirildi

Sebep:
- UI timestamp id ile backend session id'nin karışması çok turlu konuşma sahipliğini zayıflatıyordu

### Structured AI command execution düzeltmesi

Dosya:
- [src/application/backend_gateway.py](/Users/Yigit/Desktop/sentinel_root/src/application/backend_gateway.py)

Yapılan iş:
- structured AI command için ayrı hazırlık/validation yolu eklendi
- raw kullanıcı komutu için `parse_command_with_risk()` korunurken AI komutları aynı string parser'a geri sokulmamaya başlandı
- `whois`, `sqlmap` ve kontrollü shell-wrapper senaryoları için Yiğit akışını kıran UI gate dar boğazı gevşetildi

Sebep:
- AI tarafından üretilen meşru komutlar UI onayından sonra bile execution kapısında reddedilebiliyordu

### Typed validation düzeltmesi

Dosya:
- [src/core/validators.py](/Users/Yigit/Desktop/sentinel_root/src/core/validators.py)

Yapılan iş:
- raw command validation ile structured arg validation ayrıştırıldı
- query string, form payload, percent-encoded değer gibi meşru parametreler structured akışta korunmaya başlandı

Sebep:
- global regex filtresi tool-aware değildi ve meşru URL/form parametrelerini de blokluyordu

### Windows native execution ve process lifecycle düzeltmesi

Dosyalar:
- [src/core/platform_utils.py](/Users/Yigit/Desktop/sentinel_root/src/core/platform_utils.py)
- [src/core/execution_manager.py](/Users/Yigit/Desktop/sentinel_root/src/core/execution_manager.py)
- [src/core/process_manager.py](/Users/Yigit/Desktop/sentinel_root/src/core/process_manager.py)
- [src/core/tools/base.py](/Users/Yigit/Desktop/sentinel_root/src/core/tools/base.py)

Yapılan iş:
- native executable resolution merkezileştirildi
- Windows üzerinde subprocess fallback eklendi/güçlendirildi
- failed-to-start durumunda ikinci kez sahte timeout üretilmesinin önü kesildi
- process yaşam döngüsü tek terminal sonuç verecek şekilde sertleştirildi

Sebep:
- özellikle `ping` gibi native araçlarda implicit lookup ve QProcess davranışı yeterince güvenilir değildi

### Bu turun test ve dokümantasyon karşılığı

Testler:
- [src/tests/test_ui_backend_boundary.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_ui_backend_boundary.py)
- [src/tests/test_ui_widgets.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_ui_widgets.py)
- [src/tests/test_sprint1_week2.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_sprint1_week2.py)

Dokümanlar:
- [docs/yigit_stabilization_hotfix.md](/Users/Yigit/Desktop/sentinel_root/docs/yigit_stabilization_hotfix.md)
- [docs/kerem_handoff_issues.md](/Users/Yigit/Desktop/sentinel_root/docs/kerem_handoff_issues.md)

Doğrulama durumu:
- hedefli Yiğit regresyon paketi: `311 passed`
- tam lokal koşu: `1578 passed, 1 failed`
- kalan tek failure: [src/tests/test_action_planner_v2.py](/Users/Yigit/Desktop/sentinel_root/src/tests/test_action_planner_v2.py) içindeki live LLM exact-match oynaklığı

Not:
- Bu kalan failure, Yiğit-first stabilizasyon kapsamında özellikle Kerem/shared AI alanına handoff edilmek üzere ayrı bırakıldı.

## 6. Kerem'in Görmesi Gereken Net Sonuç

03.03.2026 sonrası Yiğit tarafı yalnızca UI polish yapmadı; şu alanlarda proje davranışını ciddi biçimde ileri taşıdı:

1. AI güvenlik onayı ve risk görünürlüğünü ürün akışına yerleştirdi.
2. UI'yi i18n, settings ve regression testleriyle daha kurumsal hale getirdi.
3. Komut üretim hattını benchmark ve audit testleriyle ölçülebilir hale getirdi.
4. Tool yüzeyini genişletti ve buna karşılık doğrulama/test altyapısını kurdu.
5. Intent parsing zincirini daha toleranslı ve daha deterministik hale getirdi.
6. Son stabilizasyon turunda UI/backend session ownership, structured command execution, typed validation ve Windows native execution sorunlarını kapattı.

## 7. Kerem'e Açık Handoff Noktaları

Yiğit tarafından özellikle ayrıştırılan ve Kerem/shared AI ownership altında değerlendirilmesi uygun görülen konular:

1. `WEB_VULN_SCAN` intent semantiğinin registry/executor düzeyinde drift üretmesi
2. live LLM exact-match testlerinin CI/stabilite açısından oynak olması
3. ortak AI/registry sözleşmesinde bazı behavior'ların dökümante edilen anlam ile birebir hizalı olmaması

Bu açıklar için ayrı teknik not:
- [docs/kerem_handoff_issues.md](/Users/Yigit/Desktop/sentinel_root/docs/kerem_handoff_issues.md)

## 8. Referans Commit Listesi

- `c078f8d0` - Sprint 3 close: AI-security integration, root confirmation, risk indicators, cleanup hardening, regression tests
- `f8af8429` - feat(ui): add i18n system with 11 languages and settings dialog
- `78765db8` - feat(ui): integrate i18n, layout swap, and font fixes across UI components
- `73586845` - fix(ai): add i18n command message translation and pre-compile regex
- `6da30d10` - perf(core): pre-compile regex patterns in validators and parser_framework
- `93bfef45` - test(ui): add comprehensive UI, i18n, and optimization test suites (591 tests)
- `e04b5802` - docs(sprint3.4): update all documentation for Sprint 3.4 completion
- `9dcec812` - feat(sprint3.5): hotfix - security confirmation, keyword fallback, accuracy benchmark, docs sync
- `7421e12e` - merge: dev_yigit sprint 3.5 hotfix into develop
- `a8e15998` - fix(ai): Implement 100% pipeline accuracy with DNS hard-override, JSON tolerance, and target regex tweaks
- `05778d29` - docs: Update son_durum.md with 100% Sprint 3.5 pipeline accuracy completion status
- `63507a7b` - fix(ai): enforce JSON mode for intent resolution to prevent truncation

## 9. Son Not

Bu raporun amacı "kimin alanı neydi" tartışması değil, 03.03.2026 sonrası Yiğit tarafından projeye eklenen teknik ağırlığı ve bunun mimari etkisini görünür hale getirmektir. Özellikle komut üretim hattında Yiğit'in etkisi; doğruluk, fallback, testlenebilirlik, yeni araç entegrasyonu ve UI/security bağının güçlenmesi ekseninde nettir.
