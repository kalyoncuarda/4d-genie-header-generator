# 4D Systems Genie C Header Generator

4D Systems ViSi-Genie (.4DGenie) proje dosyalarını ayrıştırarak deterministik, standartlara uygun C/C++ başlık (`.h`) dosyaları üreten bir CLI aracıdır.

## 🚀 Özellikler

- **Deterministik Çıktı:** Bileşenleri tip ve index sırasına göre sıralar.
- **İsim Normalizasyonu:** Alias metinlerini C makro standartlarına (`UPPER_SNAKE_CASE`) dönüştürür.
- **Hata Kontrolleri:** Mükerrer index veya çakışan makro isimlerini otomatik yakalar.
- **Strict Mode (`--strict`):** Alias verilmemiş bileşenler olduğunda hata fırlatır.
- **Check Mode (`--check`):** Header dosyasının güncel olup olmadığını dosyayı değiştirmeden doğrular (CI uyumlu).

## 🛠️ Desteklenen Bileşenler

- Form / Menüler (`FORM_...`)
- Butonlar (`USERBUTTON_...`, `WINBUTTON_...`)
- Metin Nesneleri (`STRINGS_...`, `STATICTEXT_...`)
- Görseller & Klavyeler (`USERIMAGES_...`, `IMAGE_...`, `KEYBOARD_...`)
- Medya & Çizimler (`VIDEO_...`, `SOUNDS_...`, `PANEL_...`, `BORDER_...`)

## 💻 Kullanım

### Header Üretme
```bash
python3 tools/generate_genie_header.py --project MainScreen.4DGenie --output include/genie_objects.h
