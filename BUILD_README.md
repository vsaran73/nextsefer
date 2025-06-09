# NextSefer - Derleme Kılavuzu

Bu belge, NextSefer'in Electron ile masaüstü uygulaması olarak nasıl derleneceğini ve paketleneceğini açıklar.

## Gereksinimler

- Python 3.11 veya üzeri
- Node.js 14 veya üzeri
- npm 6 veya üzeri
- Django 5.2 veya üzeri

## Derleme Adımları

### Otomatik Derleme

Tüm derleme sürecini otomatikleştirmek için `build_all.bat` dosyasını çalıştırın:

```
.\build_all.bat
```

Bu script şunları yapacaktır:
1. Python modüllerini hazırlayacak
2. Node.js modüllerini yükleyecek
3. Electron uygulamasını derleyecek
4. Kurulum dosyalarını dist_electron/ klasöründe oluşturacak

### Manuel Derleme

#### 1. Python Dağıtımını Hazırlama

Python dağıtımını hazırlamak için:
```
python prepare_python_dist.py
```

#### 2. Node.js Modüllerini Yükleme

Gerekli Node.js modüllerini yüklemek için:
```
npm install
```

#### 3. Electron Builder ile Paketleme

Electron uygulamasını paketlemek için:
```
npm run build
```

## Yapılandırma Dosyaları

- `package.json`: Electron uygulama yapılandırması ve bağımlılıkları
- `main.js`: Electron ana süreci
- `preload.js`: Electron renderer süreci ile güvenli iletişim
- `.electron-builder.js`: Electron Builder yapılandırması
- `run_app.py`: Django uygulamasını başlatan ana script

## Versiyon Güncelleme

Yeni bir sürüm yayınlarken şunları yapmalısınız:

1. `nextsefer/settings.py` dosyasında `APP_VERSION` değerini güncelleyin:
   ```python
   # Uygulama versiyonu
   APP_VERSION = '1.0.0'  # Yeni versiyona güncelleyin
   ```

2. `package.json` dosyasındaki versiyon değerini güncelleyin:
   ```json
   {
     "name": "nextsefer-electron",
     "version": "1.0.0",  // Yeni versiyona güncelleyin
     ...
   }
   ```

3. `main.js` dosyasındaki sürüm bilgisini güncelleyin (varsa):
   ```javascript
   const APP_VERSION = '1.0.0';  // Yeni versiyona güncelleyin
   ```

## Güncelleme Sunucusu

Otomatik güncelleme sistemi için Electron Builder'ın auto-update özelliğini kullanabilirsiniz:

- `electron-updater` modülünü package.json'a ekleyin
- Güncelleme sunucusu yapılandırmasını `.electron-builder.js` dosyasına ekleyin

## Sorun Giderme

- **Electron hataları**: Konsol çıktılarını ve DevTools ile hataları kontrol edin
- **Python hataları**: python_dist/logs/ dizinindeki log dosyalarını kontrol edin
- **Django sunucusu başlatılamıyor**: Bağımlılıkların doğru yüklendiğinden emin olun
- **Eksik Python modülleri**: prepare_python_dist.py dosyasında REQUIREMENTS listesini güncelleyin
 
 
 