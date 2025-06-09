# NextSefer Electron Uygulaması

Bu belge, NextSefer Django uygulamasının Electron sürümünün nasıl kullanılacağına dair bilgiler içerir.

## Genel Bakış

NextSefer Electron uygulaması, mevcut Django tabanlı web uygulamasını masaüstü uygulamasına dönüştüren bir kapsayıcıdır. Bu uygulama:

- Django arka ucunu yerleşik olarak çalıştırır
- Elektron tabanlı bir pencerede web uygulamasını gösterir
- Sistem tepsisinde simge ile çalışır
- Standart masaüstü uygulaması özellikleri sunar

## Gereksinimler

Bu uygulamayı geliştirmek ve çalıştırmak için aşağıdaki yazılımlara ihtiyaç vardır:

- Node.js (v14 veya üzeri)
- npm (v6 veya üzeri) 
- Python 3.8 veya üzeri
- Django ve ilgili Python paketleri

## Kurulum

### Geliştirme Ortamı Kurulumu

1. Gerekli Node.js modüllerini yükleyin:
   ```
   npm install
   ```

2. Python sanal ortamı oluşturun ve gereksinimleri yükleyin:
   ```
   pip install virtualenv
   python prepare_python_dist.py
   ```

### Uygulama Çalıştırma

Geliştirme modunda çalıştırmak için:

```
npm run dev
```

### Paket Oluşturma

Windows'ta paket oluşturmak için:

```
build.bat
```

veya manuel olarak:

```
npm install
python prepare_python_dist.py
npm run build
```

## Yapı

Uygulama aşağıdaki ana bileşenlerden oluşur:

- `main.js`: Electron'un ana süreci
- `preload.js`: Web içeriği ile ana süreç arasında iletişim sağlayan önbellek betiği
- `run_app.py`: Django sunucusunu çalıştıran Python betiği
- `prepare_python_dist.py`: Python dağıtımını hazırlayan betik

## Özellikler

- Yerleşik Django sunucusu
- Yerleşik SQLite veritabanı
- Sistem tepsisi simgesi ve menüsü
- Otomatik başlatma ve tek örnek uygulama kontrolü
- Tarayıcı penceresi UI özelleştirmeleri

## Sorun Giderme

### Django sunucusu başlatılamıyor

Eğer Django sunucusu başlatılamazsa:

1. `python_dist` dizininin doğru şekilde oluşturulduğundan emin olun
2. Gerekli Python modüllerinin yüklü olduğunu kontrol edin
3. Log dosyalarını kontrol edin

### Pencere boş görünüyor

Eğer Electron penceresi boş görünüyorsa:

1. Django sunucusunun çalıştığından emin olun
2. Dev araçlarını açarak (Ctrl+Shift+I) konsol hatalarını kontrol edin

## Lisans

Bu yazılım özeldir ve lisans bilgileri için lütfen proje sahibiyle iletişime geçin. 