# UI Regression Checklist (Sprint 3 Sonu)

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

## Önerilen Kısa Akış
1. Uygulamayı başlat.
2. `Layout` ile iki yönü test et.
3. Terminalden uzun bir komut çalıştırıp `Stop` test et.
4. Chatten mesaj gönder, geçmişi aç-kapat.
5. Settings temizleme testini çalıştır.
6. Uygulamayı kapat-aç; geçmişte boş kayıt birikimi yok mu kontrol et.
