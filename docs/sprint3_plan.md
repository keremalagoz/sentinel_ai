# 🛡️ Sprint 3: Güvenlik, Yetki ve Temizlik Planı

**Tarih:** 9 Ocak 2026
**Durum:** Planlandı
**Öncelik:** KRİTİK

Bu doküman, Sentinel AI projesinin güvenlik altyapısını kuracak olan Sprint 3 aşamasının detaylı yol haritasıdır.

---

## 🎯 Hedefler

1. **Hibrit Mimari (ExecutionManager):** Sistemin hem Docker hem de Native (host) modunda çalışabilmesini sağlamak.
2. **Güvenli Yetki Yönetimi (Pkexec):** Root yetkisi gerektiren işlemleri `sudo` olmadan, güvenli GUI (Polkit) pencereleriyle yönetmek.
3. **Güvenli Temizlik (Secure Cleaner):** Geçici dosyaları ve hassas verileri diskten güvenli bir şekilde (shredding) silmek.
4. **Girdi Doğrulama (Input Validation):** Komut enjeksiyonlarını engellemek için tüm kullanıcı girdilerini denetlemek.

---

## 🏗️ Mimari Tasarım

### 1. Execution Manager (`src/core/execution_manager.py`)
Sistemin beyni olacak bu modül, çalışma ortamına göre strateji belirleyecek.

*   **Görev:** Docker varlığı kontrolü.
*   **Strateji:** 
    *   Docker varsa -> `ExecutionMode.DOCKER` (Root yetkisi container içinde zaten var).
    *   Docker yoksa(Linux) -> `ExecutionMode.NATIVE` (Hassas komutlar için `pkexec` kullanılır).
*   **Çıktı:** Komutları ve dosya yollarını ( `/tmp` vs `/app/output` ) normalize eder.

### 2. Secure Cleaner (`src/core/cleaner.py`)
Artık veri bırakmayan çöpçü mekanizması.

*   **Yöntem:**
    *   `os.remove` ile silmeyi dene.
    *   Yetki hatası (`PermissionError`) alırsan `pkexec rm` kullan.
*   **Güvenlik:** Sadece whitelist (beyaz liste) içindeki dizinlerde çalışır. `..` (path traversal) saldırılarına karşı korumalıdır.
*   **Şifreli Silme:** Dosya silinmeden önce rastgele byte'lar ile üzerine yazılır.

### 3. Pkexec Wrapper & Process Manager
Kullanıcı deneyimi odaklı yetki yönetimi.

*   **Hata Yakalama:** 
    *   `Exit Code 126`: "Kullanıcı İptal Etti" -> İşlemi nazikçe durdur.
    *   `Exit Code 127`: "Hatalı Şifre" -> Tekrar sor.
*   **UI:** Şifreler asla kod içinde tutulmaz, işletim sistemi arayüzü kullanılır.

---

## 📅 Uygulama Planı (Task List)

### Faz 1: Altyapı (Core)
- [ ] **Task 3.1:** `ExecutionManager` sınıfını oluştur.
    - Docker detection logic.
    - Platform (OS) detection logic.
- [ ] **Task 3.2:** `SecureCleaner` sınıfını oluştur.
    - Whitelist mekanizması.
    - Secure delete (overwrite) fonksiyonu.
- [ ] **Task 3.3:** `InputValidator` sınıfını oluştur.
    - IP/Domain regex kontrolleri.
    - Shell injection koruması.

### Faz 2: Entegrasyon (Integration)
- [ ] **Task 3.4:** `ProcessManager` güncellemesi.
    - Yeni `ExecutionManager` yapısına geçiş.
    - `start_process` metodunun `pkexec` desteklemesi.
- [ ] **Task 3.5:** `main.py` başlangıç ve kapanış entegrasyonu.
    - Açılışta eski session temizliği.
    - Kapanışta `SecureCleaner` tetiklenmesi.

### Faz 3: Test
- [ ] **Task 3.6:** "User Cancellation" testi (Şifre girmeyip iptal etme).
- [ ] **Task 3.7:** "Root Cleanup" testi (Sudo ile oluşan dosyayı silme).

---

## ⚠️ Riskler ve Önlemler

| Risk | Önlem |
|------|-------|
| `rm -rf /` kazası | Sadece `/tmp/sentinel_` gibi belirli prefix'li dosyalara izin verilecek (Whitelist). |
| Windows uyumsuzluğu | `ExecutionManager` Windows'ta otomatik olarak Native modu kapatıp uyaracak veya kısıtlı modda çalışacak. |
| Performans (Shredding) | Çok büyük dosyalarda (karyabaytlarca) overwrite işlemi atlanabilir, sadece silme yapılabilir. |

---

*Bu plan, kullanıcı onayı ile 3. Sprint kapsamında hayata geçirilecektir.*
