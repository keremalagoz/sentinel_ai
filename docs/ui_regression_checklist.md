# UI Regression Checklist (Sprint 3.4 Sonu)

Bu liste, `develop` öncesi 3-5 dakikalık hızlı doğrulama için hazırlanmıştır.

## 1) Header ve Yerleşim
- Uygulama açıldığında üst barda şu butonlar görünür: `Hist`, `+C`, `+T`, `Layout`, `Settings`.
- Varsayılan düzen: **Chat üstte**, **Terminal altta**.
- `Layout` butonu ile düzen sağlı-solluya geçer; tekrar basınca altlı-üstlüye döner.
- Pencere daraltıldığında header butonları üst üste binmez.

## 2) Chat Davranışı
- Chat giriş alanında sadece gönder butonu (`->`) görünür.
- Chat tarafında ayrı bir stop butonu görünmez.
- AI komut kartı (`Run` / `Copy`) çalışır.
- Sohbet geçmişi penceresi açılır, liste satırları ve tarih görünümü düzgündür.

## 3) Terminal Davranışı
- Terminal sekmeli yapıdadır; `+T` ile yeni terminal açılır.
- Terminal sekmesi kapatma (`x`) çalışır.
- Komut çalışırken terminal input yanında `Stop` butonu görünür.
- Komut bittiğinde terminalde `Stop` butonu kaybolur.

## 4) Splitter ve Scroll
- Chat/Terminal boyutu splitter ile sürüklenerek değiştirilebilir.
- Sürükleme sırasında chat mesaj listesi zıplamaz/yukarı kaçmaz.

## 5) Geçmiş Temizleme
- `Settings -> Clean Old Sessions Now` aksiyonu hata vermeden çalışır.
- Çok eski kayıtlar/boş sohbetler temizlenir.
- Uygulama kapanıp açıldığında boş `Untitled` sohbet birikimi oluşmaz.

## 6) Güvenlik Giriş Kontrolü (Hızlı)
- İzin verilmeyen komut terminalden girildiğinde reddedilir ve uyarı logu görülür.
- İzinli komutlar çalışır.

## 7) i18n / Dil Desteği (Sprint 3.4)
- `Settings` → Dil dropdown'unda 11 dil listelenir (EN, TR, ES, ZH, JA, AR, DE, RU, FR, PT, HI).
- Dil değiştirildiginde tüm header butonları ve etiketler anında güncellenir.
- Chat giriş alanı placeholder'ı seçilen dilde görünür.
- Terminal prompt metni seçilen dilde görünür.
- Settings diyalogu etiketleri seçilen dilde görünür.
- Uygulama yeniden başlatıldığında seçilen dil korunur.
- Olmayan bir çeviri anahtarı için İngilizce fallback çalışır.

## 8) Ayarlar Diyalogu (Sprint 3.4)
- `Settings` butonu diyalogu açar.
- Dil seçimi dropdown çalışır ve değişiklik anında uygulanır.
- Font boyutu slider çalışır (11-24px arası).
- Font boyutu değiştiğinde chat balonları yeniden oluşturulmadan güncellenir.
- `Clean Old Sessions Now` butonu hata vermeden çalışır.

## 9) Layout Swap (Sprint 3.4)
- `Layout` butonu ile Chat/Terminal pozisyonu değişir.
- Dikey düzende: Chat üst, Terminal alt (veya ters).
- Yatay düzende: Chat sol, Terminal sağ (veya ters).
- Layout değiştirme sırasında mevcut içerik korunur.

## 10) Performans (Sprint 3.4)
- Chat geçmişi kaydı anlık disk yazımı yapmaz (debounce 500ms).
- Pencere yeniden boyutlandırılırken hissedilir takılma olmaz.
- Font değişikliği anlık uygulanır, gecikme yok.
- Çoklu terminal sekmesi açma/kapama akıcıdır.

## Önerilen Kısa Akış
1. Uygulamayı başlat.
2. `Settings` → dili Türkçe'ye çevir, etiketleri kontrol et.
3. `Settings` → dili Japonca'ya çevir, font boyutunu 18 yap.
4. `Layout` ile iki yönü test et.
5. Terminalden uzun bir komut çalıştırıp `Stop` test et.
6. Chatten mesaj gönder, geçmişi aç-kapat.
7. Settings temizleme testini çalıştır.
8. Uygulamayı kapat-aç; seçilen dil ve font korunuyor mu kontrol et.
9. Geçmişte boş kayıt birikimi yok mu kontrol et.
