# Benchmark Results

Bu rapor, en son 200 vakalik iki dilli benchmark kosusunun sonucunu ozetler.

- Dataset: 200 prompt
- Dil dagilimi: 100 Turkce, 100 Ingilizce
- Model: qwen2.5:3b
- Mod: hierarchical
- Kaynak cikti: temp/prompt_benchmark_200_bilingual.json
- Karsilastirma CSV: temp/prompt_benchmark_200_bilingual_comparisons.csv
- Canli log: temp/prompt_benchmark_200_bilingual.log

## Executive Summary

Sistem intent bulma seviyesinde kabul edilebilir durumda, ancak komutun calistirilabilir spesifikasyonuna inildiginde ciddi kayip var. En kritik zayifliklar parametre cikarma, info vs unknown ayrimi ve web intent ayriminda toplanmis durumda.

Ana sonuc:

- Intent accuracy yuksek: 88.5%
- Exact match dusuk: 23.5%
- Target extraction orta seviye: 74.5%
- Param extraction zayif: 33.0%
- Clarification davranisi guclu: 95.0%
- Category accuracy yuksek: 94.5%

Bu tablo su anlama geliyor:

- Sistem cogu vakada kullanicinin ne istedigini genel olarak anliyor.
- Ancak hangi hedefe, hangi alt parametrelerle, hangi komut semantigiyle gidilecegi noktasinda hata birikiyor.
- Uretim ortaminda salt intent accuracy yeterli degil; exact match ve param accuracy belirgin bicimde iyilestirilmeli.

## Overall Metrics

| Metrik | Deger |
|---|---:|
| Toplam vaka | 200 |
| Cozulen vaka | 200 |
| Hata | 0 |
| Dogru intent | 177 |
| Yanlis intent | 23 |
| Intent accuracy | 88.5% |
| Exact match | 23.5% |
| Target accuracy | 74.5% |
| Params accuracy | 33.0% |
| Clarification accuracy | 95.0% |
| Category accuracy | 94.5% |
| Prompt quality | 82.1% |
| Ortalama latency | 1257.6 ms |
| Min latency | 578.0 ms |
| Max latency | 5625.0 ms |
| Stage 1 ortalama latency | 151.3 ms |
| Stage 2 ortalama latency | 1106.3 ms |
| Ortalama confidence | 91.1% |
| Dogru kararlarda confidence | 94.9% |
| Yanlis kararlarda confidence | 62.0% |
| Confidence calibration gap | 2.6% |
| Keyword bypass count | 142 |

## Locale Split

| Locale | Vaka | Intent | Exact Match | Target | Params | Clarification | Category | Prompt Quality | Avg Latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Turkce | 100 | 88.0% | 24.0% | 71.0% | 34.0% | 95.0% | 96.0% | 81.6% | 1207.3 ms |
| Ingilizce | 100 | 89.0% | 23.0% | 78.0% | 32.0% | 95.0% | 93.0% | 82.5% | 1307.8 ms |

Yorum:

- Ingilizce taraf intent ve target extraction'da biraz daha guclu.
- Turkce taraf category ve params alaninda biraz daha duzgun.
- Her iki dilde de exact match dusuk; bu sorun dil bazli degil, mimari olarak extraction katmaninda.
- Ingilizce tarafin latency'si daha yuksek.

## Top Failure Clusters

En sik karisikliklar:

| Adet | Beklenen | Gerceklesen |
|---:|---|---|
| 6 | info_query | unknown |
| 4 | web_dir_enum | web_vuln_scan |
| 3 | unknown | info_query |
| 2 | web_dir_enum | brute_force_http |
| 1 | service_detection | host_discovery |
| 1 | web_vuln_scan | vuln_scan |
| 1 | whois_lookup | dns_lookup |
| 1 | subdomain_enum | dns_lookup |
| 1 | brute_force_http | unknown |
| 1 | unknown | dns_lookup |
| 1 | dns_lookup | info_query |
| 1 | info_query | sql_injection |

Bu dagilimdan cikan net sonuc:

1. Info ve belirsiz niyetler birbirine karisiyor.
2. Web ailesindeki intentler yeterince ayristirilmiyor.
3. Recon ailesinde DNS / WHOIS / subdomain cizgisi bazi vakalarda dagiliyor.

## Intent-by-Intent Assessment

| Intent | Vaka | Accuracy | Exact Match | Target | Params | Degerlendirme |
|---|---:|---:|---:|---:|---:|---|
| host_discovery | 16 | 100.0% | 31.2% | 87.5% | 31.2% | Siniflandirma guclu, paramlar gereginden fazla veya yanlis doluyor |
| port_scan | 18 | 100.0% | 33.3% | 88.9% | 33.3% | Intent guclu, param extraction fazla girdi uretme egiliminde |
| service_detection | 14 | 92.9% | 0.0% | 85.7% | 7.1% | Param semantigi cok zayif; service detection bayragi ve port mantigi karisiyor |
| os_detection | 14 | 100.0% | 28.6% | 85.7% | 28.6% | Intent iyi, ama ekstra param uretimi exact match'i dusuruyor |
| vuln_scan | 16 | 100.0% | 0.0% | 75.0% | 0.0% | Intent tam isabetli, fakat params sifira yakin; bu en kritik extraction zayifligi |
| ssl_scan | 14 | 100.0% | 0.0% | 85.7% | 0.0% | SSL niyeti bulunuyor ama tool seviyesi param mantigi oturmamis |
| web_dir_enum | 14 | 57.1% | 28.6% | 71.4% | 28.6% | En zayif web intenti; web vuln ve brute force ile karisiyor |
| web_vuln_scan | 12 | 91.7% | 0.0% | 41.7% | 0.0% | Intent cogu zaman dogru ama target/param extraction yetersiz |
| dns_lookup | 14 | 92.9% | 71.4% | 85.7% | 92.9% | Recon tarafinin en saglam intentlerinden biri |
| whois_lookup | 10 | 90.0% | 90.0% | 100.0% | 90.0% | En saglam intentlerden biri |
| subdomain_enum | 12 | 91.7% | 66.7% | 83.3% | 66.7% | Genel olarak iyi, ara ara DNS lookup'a kayiyor |
| brute_force_ssh | 10 | 100.0% | 0.0% | 80.0% | 0.0% | Intent iyi, ancak varsayilan veya hatali param doldurma yuksek |
| brute_force_http | 10 | 90.0% | 0.0% | 50.0% | 10.0% | Hedef ve form parametresi mantigi zayif |
| sql_injection | 10 | 100.0% | 0.0% | 30.0% | 0.0% | Intent dogru ama URL/arg extraction calismiyor |
| info_query | 12 | 41.7% | 8.3% | 58.3% | 91.7% | En zayif intent sinifi |
| unknown | 4 | 0.0% | 0.0% | 25.0% | 100.0% | Belirsiz komutlar dogru clarification yerine baska intentlere kayiyor |

## Extraction Analysis

Bu benchmarkin en kritik icgorusu intent ve extraction katmanlarinin birbirinden ayrismasi oldu.

- Toplam intent dogru vaka: 177
- Intent dogru ama target yanlis: 45
- Intent dogru ama params yanlis: 124
- Intent dogru ama exact match degil: 130

Bu su demek:

- Asil darbo gaz intent classification degil.
- Asil darbo gaz target ve params extraction.
- Intent accuracy tek basina kaliteyi gizliyor; exact match ve params accuracy esas odak olmali.

En cok param kaybi ureten intentler:

| Adet | Intent |
|---:|---|
| 16 | vuln_scan |
| 14 | ssl_scan |
| 13 | service_detection |
| 12 | port_scan |
| 12 | web_vuln_scan |
| 11 | host_discovery |
| 10 | os_detection |
| 10 | web_dir_enum |
| 10 | brute_force_ssh |
| 10 | sql_injection |
| 9 | brute_force_http |

Buradaki ortak desen, modelin cok sayida gereksiz veya normalize edilmemis param uretmesi. CSV incelendiginde ayni vaka icin asagidaki tipte sapmalar goruluyor:

- Beklenmeyen ek anahtarlar uretme
- Varsayilan scan argumanlarini gereksiz yere params'a yazma
- Target bosken semantik placeholder dondurme
- Web intentlerde farkli arac ailelerinin param semantiklerini karistirma

## Turkish vs English Weaknesses

### Turkce tarafin belirgin sorunlari

- `banner grab yap hedef sunucuya` -> `host_discovery`
- `gobuster ile gizli path ara` -> `web_vuln_scan`
- `nmap nedir ne ise yarar` -> `unknown`
- `merhaba bugun hava nasil` -> `info_query`
- `birseyler yap` -> `info_query`

Yorum:

- Turkce serbest ifade ve sohbet dili sistemde kolayca `info_query` veya tarama intentine kayabiliyor.
- Arac adini iceren ama acik operasyon istemeyen bilgi sorulari yeterince ayrilmiyor.

### Ingilizce tarafin belirgin sorunlari

- `Test the login form at the target system with brute force` -> `unknown`
- `Handle the target system somehow` -> `dns_lookup`
- `I need help with a task but I am not sure what exactly` -> `info_query`
- `Discover hidden paths on https://shop.example.com` -> `web_vuln_scan`
- `Run directory brute force against http://192.168.1.50` -> `brute_force_http`

Yorum:

- Ingilizce web directory semantics hala brute force ve vuln semantics ile karisiyor.
- Belirsiz Ingilizce promptlar bazen alakasiz recon intentine kayiyor.

## Root Cause Summary

En onemli eksikler:

1. `info_query` ve `unknown` ayrimi zayif.
2. Web intent taksonomisi yeterince keskin degil.
3. Param extraction intent classification'in gerisinde.
4. Bazi intentlerde benchmark beklentisi ile modelin param semantigi arasinda tasarimsal uyumsuzluk olabilir.
5. Stage 2 parse hatalari tamamen bitmemis.

## Priority Action Plan

### P0

- `info_query` ile `unknown` ayrimini netlestir.
- Belirsiz promptlarda clarification zorunlulugunu daha sert uygula.
- Web dir enum ile web vuln scan ve brute force HTTP intentlerini ayrisan orneklerle yeniden promptla.

### P1

- Param extraction icin intent bazli whitelist / normalizer ekle.
- Gereksiz param doldurmayi kes.
- Varsayilan tool argumentlerini params alanina yazmama kuralini getir.

### P2

- `ssl_scan`, `vuln_scan`, `sql_injection`, `brute_force_*` icin beklenen param semalarini benchmark tarafinda yeniden gozden gecir.
- Intent dogru olsa bile exact match'i dusuren placeholder / extra-field davranisini temizle.

## Recommended Success Criteria

Bir sonraki iterasyon icin hedefler:

- Intent accuracy: >= 92%
- Exact match: >= 45%
- Target accuracy: >= 85%
- Params accuracy: >= 65%
- `info_query` accuracy: >= 75%
- `web_dir_enum` accuracy: >= 85%
- `unknown` accuracy: >= 70%

## Final Assessment

Sistem bugun icin sunlari iyi yapiyor:

- Ana scanning ailelerini dogru intent'e baglama
- Category secimi
- Clarification davranisinin genel disiplini
- DNS / WHOIS / Subdomain gibi bazi recon intentleri

Sistem bugun icin sunlarda yetersiz:

- Calistirilabilir ve temiz parametre cikarma
- Bilgi sorusu ile belirsiz istem ayrimi
- Web intent ailesi ayrimi
- Exact match odakli komut spesifikasyonu

Kisa sonuc:

Bu mimari "kullanici ne istiyor" sorusuna cogu zaman cevap verebiliyor, ancak "hangi hedefe hangi parametrelerle hangi komut semantiginde gitmeli" sorusunda henuz yeterince guvenilir degil.