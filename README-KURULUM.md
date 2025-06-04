# 🚀 Surveillance System - Windows Kurulum Kılavuzu

Bu kılavuz, Surveillance System projesini Windows ortamında kurmanız için gerekli tüm adımları içerir.

## 📋 Ön Koşullar

Kuruluma başlamadan önce aşağıdaki yazılımların yüklü olduğundan emin olun:

### Zorunlu Gereksinimler
- ✅ **Docker Desktop** (v4.0+)
- ✅ **PowerShell 5.1+** (Windows ile birlikte gelir)
- ✅ **Git** (opsiyonel, geliştirme için önerilir)

### Opsiyonel Gereksinimler
- 🐍 **Python 3.8+** (geliştirme için)
- 📱 **Node.js 16+** (mobile app geliştirme için)
- 🔧 **Visual Studio Code** (geliştirme için önerilen IDE)

## 🚀 Hızlı Kurulum

### 1. Temel Sistem Kurulumu

En basit kurulum için aşağıdaki komutu çalıştırın:

```powershell
# PowerShell'i yönetici olarak çalıştırın
PowerShell -ExecutionPolicy Bypass -File setup-windows.ps1
```

### 2. Geliştirme Ortamı Kurulumu

Geliştirme yapmak istiyorsanız:

```powershell
# Önce ana sistemi kurun
PowerShell -ExecutionPolicy Bypass -File setup-windows.ps1 -DevMode

# Sonra geliştirme araçlarını kurun
PowerShell -ExecutionPolicy Bypass -File setup-dev.ps1
```

### 3. Hızlı Başlatma

Sistem kurduktan sonra başlatmak için:

```powershell
# Sistemi başlat
.\quick-start.ps1

# Durumu kontrol et
.\check-status.ps1
```

## 🛠️ Detaylı Kurulum Seçenekleri

### Ana Kurulum Scripti Parametreleri

```powershell
# Ön koşul kontrollerini atla
.\setup-windows.ps1 -SkipPrerequisites

# Geliştirme modu (monitoring dahil)
.\setup-windows.ps1 -DevMode

# Hızlı kurulum (sadece temel servisler)
.\setup-windows.ps1 -Quick

# Sadece Docker imajlarını build et
.\setup-windows.ps1 -BuildOnly

# Belirli ortam için kur (production/staging/development)
.\setup-windows.ps1 -Environment "production"

# Sistemi temizle
.\setup-windows.ps1 clean
```

### Geliştirme Ortamı Parametreleri

```powershell
# Python kurulumunu atla
.\setup-dev.ps1 -SkipPython

# Node.js kurulumunu atla
.\setup-dev.ps1 -SkipNodejs

# Geliştirme araçlarını atla
.\setup-dev.ps1 -SkipTools

# Tam kurulum (ana sistem + geliştirme)
.\setup-dev.ps1 -FullSetup
```

## 📊 Sistem Kontrolü ve Yönetimi

### Durum Kontrol Komutları

```powershell
# Temel durum kontrol
.\check-status.ps1

# Detaylı sistem bilgileri
.\check-status.ps1 -Detailed

# JSON formatında çıktı
.\check-status.ps1 -Json

# Sürekli izleme modu
.\check-status.ps1 -Watch
```

### Sistem Yönetim Komutları

```powershell
# Sistemi başlat
.\quick-start.ps1

# Sistemi durdur
.\quick-start.ps1 -Stop

# Sistemi yeniden başlat
.\quick-start.ps1 -Restart

# Sistem durumunu göster
.\quick-start.ps1 -Status

# Tüm servislerin loglarını göster
.\quick-start.ps1 -Logs

# Belirli bir servisin loglarını göster
.\quick-start.ps1 -Logs -Service "api_gateway"
```

## 🌐 Servis URL'leri

Kurulum tamamlandıktan sonra aşağıdaki URL'lerden servislere erişebilirsiniz:

| Servis | URL | Açıklama |
|--------|-----|----------|
| **API Gateway** | http://localhost:8000 | Ana API endpoint |
| **API Docs** | http://localhost:8000/docs | Swagger/OpenAPI dokümantasyonu |
| **Grafana** | http://localhost:3000 | Monitoring dashboard (admin/admin123) |
| **Prometheus** | http://localhost:9090 | Metrics collection |
| **AI Dashboard** | http://localhost:8001 | AI servisleri dashboard |
| **Edge Service** | http://localhost:8002 | Video processing |
| **VMS Service** | http://localhost:8003 | Video management |
| **Ingest Service** | http://localhost:8004 | Data ingestion |
| **Prompt Service** | http://localhost:8005 | AI prompt management |
| **RAG Service** | http://localhost:8006 | Retrieval-Augmented Generation |
| **Notifier** | http://localhost:8007 | Notification system |

## 🛠️ Geliştirme Araçları

### Python Sanal Ortamı

```powershell
# Sanal ortamı aktif et
.\venv\Scripts\Activate.ps1

# Paketleri kur
pip install -r requirements.txt

# Testleri çalıştır
pytest

# Kodu formatla
black .

# Kod kontrolü
flake8 .
```

### Docker Komutları

```powershell
# Tüm servisleri build et
docker-compose build

# Servisleri başlat
docker-compose up -d

# Servisleri durdur
docker-compose down

# Logları görüntüle
docker-compose logs -f

# Belirli bir servisin içine gir
docker-compose exec api_gateway bash
```

### Makefile Komutları

```bash
# Yardım
make help

# Kurulum
make install

# Başlatma
make start

# Durdurma
make stop

# Test
make test

# Code formatting
make format

# Linting
make lint
```

## 🐛 Sorun Giderme

### Yaygın Sorunlar ve Çözümleri

#### Docker Çalışmıyor
```powershell
# Docker Desktop'ı başlatın
# Windows + R -> "Docker Desktop" yazın ve Enter'a basın

# Docker servisinin durumunu kontrol edin
docker version
```

#### Port Çakışması
```powershell
# Kullanılan portları kontrol edin
netstat -an | findstr ":8000"

# Conflicting servisleri durdurun veya farklı port kullanın
```

#### Bellek Yetersizliği
```powershell
# Docker Desktop ayarlarından memory limitini artırın
# Settings > Resources > Advanced > Memory
```

#### Permission Hataları
```powershell
# PowerShell'i yönetici olarak çalıştırın
# Windows + X -> "Windows PowerShell (Admin)"
```

### Log İnceleme

```powershell
# Tüm servis logları
docker-compose logs

# Belirli bir servisin logları
docker-compose logs api_gateway

# Son 100 satır log
docker-compose logs --tail=100

# Canlı log takibi
docker-compose logs -f
```

### Sistem Temizleme

```powershell
# Sistemı tamamen temizle
.\setup-windows.ps1 clean

# Docker önbelleğini temizle
docker system prune -a

# Volumeleri sil
docker volume prune
```

## 📁 Proje Yapısı

```
surveillance-system/
├── 📄 setup-windows.ps1      # Ana kurulum scripti
├── 📄 setup-dev.ps1          # Geliştirme ortamı scripti
├── 📄 quick-start.ps1        # Hızlı başlatma scripti
├── 📄 check-status.ps1       # Durum kontrol scripti
├── 📄 docker-compose.yml     # Docker servis tanımları
├── 📄 .env                   # Ortam değişkenleri
├── 📁 api_gateway/           # API Gateway servisi
├── 📁 edge_service/          # Edge computing servisi
├── 📁 vms_service/           # Video management
├── 📁 rag_service/           # RAG AI servisi
├── 📁 notifier/              # Bildirim servisi
├── 📁 monitoring/            # Prometheus & Grafana
├── 📁 mobile-app/            # React Native mobil app
├── 📁 data/                  # Veri depolama
└── 📁 logs/                  # Log dosyaları
```

## 🔒 Güvenlik Notları

- Üretim ortamında `.env` dosyasındaki şifreleri değiştirin
- HTTPS kullanımını etkinleştirin
- API anahtarlarını güvenli bir şekilde saklayın
- Firewall kurallarını yapılandırın
- Düzenli güvenlik güncellemelerini takip edin

## 📞 Destek

Sorun yaşarsanız:

1. 📋 `.\check-status.ps1 -Detailed` ile detaylı durum kontrolü yapın
2. 📝 `docker-compose logs` ile logları inceleyin
3. 🔄 `.\quick-start.ps1 -Restart` ile sistemi yeniden başlatın
4. 🧹 `.\setup-windows.ps1 clean` ile sistemi temizleyin ve yeniden kurun

## 🎯 Sonraki Adımlar

Kurulum tamamlandıktan sonra:

1. 📖 [Kullanım Kılavuzu](docs/user-guide.md)'nu inceleyin
2. 🔧 [API Dokümantasyonu](http://localhost:8000/docs)'nu keşfedin
3. 📊 [Monitoring Dashboard](http://localhost:3000)'u kurmanızı kontrol edin
4. 🧪 Test verilerinizi yükleyin ve sistemi deneyin

---

💡 **İpucu**: Kurulum sorunları için log dosyalarını kontrol etmeyi unutmayın!
