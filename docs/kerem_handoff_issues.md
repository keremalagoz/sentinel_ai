# Kerem Handoff Issues

**Tarih:** 7 Mart 2026  
**Kaynak:** Yiğit stabilization uygulaması sonrası açık bırakılan ortak/AI alanları

---

## 1. Live LLM Exact-Match Test Oynaklığı

**Alan:** `src/tests/test_action_planner_v2.py::test_intent_resolver`  
**Etki:** Tam local test koşusunda kalan tek kırık bu test.  
**Belirti:** `ping taramasi yap` ve `acik portlari bul` gibi girdiler canlı modele göre bazen `unknown` dönebiliyor.  
**Reproducer:**

```powershell
$env:PYTHONPATH='.'
pytest src/tests/test_action_planner_v2.py -q
```

**Kök neden:**
- Test doğrudan canlı LLM'den exact intent eşleşmesi bekliyor.
- Orchestrator fallback/keyword hard-override davranışı bu testin sınırları dışında kalıyor.
- Test, deterministic ürün davranışını değil model oynaklığını ölçüyor.

**Önerilen owner action:**
- Bu testi opt-in integration/smoke test olarak işaretle.
- CI/blocking suite için resolver stub veya deterministic fallback yolunu test et.

---

## 2. AI / Registry Semantik Drift

**Alan:** intent -> registry -> execution sözleşmesi  
**Etki:** Bazı intent isimleri ile gerçek tool davranışı bire bir örtüşmüyor.  
**Örnek:** `WEB_VULN_SCAN` intent'i dökümantasyon ve kullanıcı beklentisinde web vulnerability scan iken, mevcut execution tarafında fingerprinting ağırlıklı alternatif yollara sapabiliyor.

**Kök neden:**
- Tool registry metadata, AI intent semantiği ve gerçek execution mapping zaman içinde ayrı yönlerde evrilmiş.
- Testlerin bir kısmı mevcut drift'i "beklenen davranış" olarak sabitlemiş olabilir.

**Önerilen owner action:**
- Her intent için tek satırlık ürün sözleşmesi çıkar.
- Registry metadata, orchestrator tool seçimi ve execution mapping'i bu sözleşmeye göre yeniden hizala.
- Drift'i kilitleyen testleri ürün sözleşmesine göre güncelle.

---

## 3. Structured Command Contract Governance

**Alan:** `FinalCommand` / orchestrator command payload biçimi  
**Etki:** UI tarafı artık structured payload bekliyor; ortak AI alanında bu payload biçiminin kontrollü evrimi önemli hale geldi.

**Kök neden:**
- Daha önce AI komutları string'e indirgenip tekrar parse edildiği için payload sözleşmesi kritik değildi.
- Stabilization sonrası structured payload ürün akışının birinci sınıf girdisi oldu.

**Önerilen owner action:**
- `executable`, `arguments`, `requires_root`, `risk_level` alanlarını resmi contract olarak dokümante et.
- Yeni tool/intent eklemelerinde bu payload şeması için regression test zorunlu kıl.

---

## Not

Bu dosyadaki başlıklar bilinçli olarak Yiğit hotfix turunda kodda büyütülmedi. Gerekçe: kullanıcı tercihi doğrultusunda Kerem alanına minimum müdahale edildi; yalnızca Yiğit akışını doğrudan kıran katmanlar düzeltildi.
