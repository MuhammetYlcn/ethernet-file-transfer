# Ethernet Transfer Pro

Bu proje, **Python 3**, **PyQt6** ve yerel **TCP Soketleri** kullanılarak geliştirilmiş, çoklu iş parçacıklı (multi-threaded) bir yüksek hızlı yerel ağ (LAN/Ethernet) dosya ve klasör transfer uygulamasıdır. Herhangi bir bulut servisine veya internet bağımlılığına ihtiyaç duymadan, yerel ağ bant genişliğinizi maksimum düzeyde kullanarak devasa boyutlardaki dosyaları bilgisayarlar arasında taşımak için tasarlanmıştır.

## 🚀 Özellikler
* **Klasör Gönderim Desteği:** Seçilen klasörleri arka planda anlık olarak otomatik `.zip` formatına sıkıştırır ve alıcı bilgisayarda dinamik olarak klasör şeklinde dışarı çıkartır.
* **Büyük Dosya Akışı:** Bellek sızıntılarını ve yüksek RAM kullanımını önlemek için veri blokları halinde akış (`1MB BUFFER_SIZE`) mekanizmasıyla optimize edilmiştir. GB'larca boyuttaki dosyaları sorunsuz transfer eder.
* **Anlık Analiz ve Metrikler:** Transfer esnasında anlık ilerleme yüzdesini (Progress Bar), aktarım hızını (`MB/s`) ve dinamik kalan süre (ETA) hesaplamasını gösterir.
* **Donmayan Arayüz (Non-Blocking UI):** Ağ ve I/O (girdi/çıktı) gibi ağır işlemler kullanıcı arayüzünü kilitlememesi için ayrı iş parçacıklarına (`SenderThread` ve `ReceiverThread`) aktarılmıştır.
* **Kurulumsuz Kullanım:** `.exe` formatına dönüştürülebilir yapısı sayesinde Python yüklü olmayan bilgisayarlarda da doğrudan çalıştırılabilir.

## 🛠️ Mimari ve Protokol Mantığı
Uygulama, verilerin eksiksiz ve hatasız iletilmesi amacıyla güvenilir **TCP Soket** (`socket.SOCK_STREAM`) mimarisini kullanır.

1. **El Sıkışma (Handshake):** Gönderici `0.0.0.0:5005` portunu dinlemeye başlar ve alıcı bağlandığında ona dosya adı ve boyutunu içeren `dosya_adi|boyut` metadatasını gönderir.
2. **Onay (Acknowledgement):** Alıcı veriyi doğrular ve göndericiye `"OK"` sinyali iletir.
3. **Veri Akışı (Data Streaming):** Gönderici dosyayı 1MB'lık parçalar halinde okuyup sokete yazar; alıcı ise bu tamponu (buffer) anlık olarak yakalayıp doğrudan diske yazar.

## 💻 Kullanılan Teknolojiler
* **Arayüz Frameworkü:** PyQt6
* **Eşzamanlılık (Concurrency):** `QThread`, `pyqtSignal`
* **Ağ Programlama:** Python `socket` modülü (TCP Protokolü)
* **Dosya İşlemleri:** `shutil`, `zipfile`, `os`

## 🔧 Kurulum ve Çalıştırma (Kaynak Kod)

### Gereksinimler
Bilgisayarınızda Python 3.x sürümünün kurulu olduğundan emin olun. Ardından gerekli arayüz kütüphanesini yükleyin:
```bash
pip install PyQt6
