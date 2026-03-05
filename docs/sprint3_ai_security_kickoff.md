# Sprint 3 AI + Güvenlik Entegrasyonu Kickoff

> Durum Notu (4 Mart 2026): Bu doküman kickoff hedeflerini içerir. Uygulanan/güncel durum için `son_durum.md`, `docs/sprint_roadmap.md` ve `docs/sprint_3_5_plan.md` referans alınmalıdır.

## Hedef
AI tarafının ürettiği komutların güvenlik katmanından geçip Terminal akışına kontrollü şekilde aktarılması.

## Öncelik Sırası
1. **Intent -> Command izlenebilirliği**
   - AI yanıtından çıkan komutun hangi resolver/katmandan geldiği loglansın.
2. **Whitelist/arg validator sertleştirme**
   - Komut + argüman denetimleri için negatif test senaryoları artırılsın.
3. **Risk seviyesi etiketi**
   - Komutlar `safe / caution / root-required` gibi seviyelerle UI/terminalde işaretlensin.
4. **Execution öncesi guardrail**
   - Root isteyen komutlarda net kullanıcı onayı ve görünür uyarı akışı.
5. **Audit trail**
   - Session bazlı: user prompt, ai message, önerilen komut, parse sonucu, execution sonucu.

## Kısa Doğrulama Kriterleri
- İzin dışı komutlar hiçbir yoldan çalıştırılamaz.
- İzinli komutlarda yanlış argümanlar güvenli şekilde reddedilir.
- Root gerektiren komutlar açık şekilde işaretlenir.
- Başarısız/başarılı tüm komut akışları loglarda izlenebilir.

## Not
UI regression kontrolü için: [ui_regression_checklist.md](ui_regression_checklist.md)
