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
```

### Strict Mode (alias eksikse hata ver)

```bash
python3 tools/generate_genie_header.py --project MainScreen.4DGenie --output include/genie_objects.h --strict
```

### Check Mode (CI için, dosyayı değiştirmeden günceli doğrula)

```bash
python3 tools/generate_genie_header.py --project MainScreen.4DGenie --output include/genie_objects.h --check
```

## 📁 Klasör Yapısı

```
tools/    -> generate_genie_header.py (ana script)
tests/    -> test_generate_genie_header.py (otomatik testler)
```

## ✅ Testler

Bu proje için 18 otomatik test yazılmıştır (`tests/test_generate_genie_header.py`).

Testleri çalıştırmak için (proje kök dizinindeyken):

```bash
pip3 install pytest --break-system-packages
python3 -m pytest tests/ -v
```

**Not:** 2 test (`test_determinizm_gercek_projede`, `test_gercek_proje_uctan_uca`) gerçek bir `.4DGenie` proje dosyası gerektirir. Bu dosya gizlilik nedeniyle repository'ye eklenmemiştir. Bu dosya olmadan çalıştırıldığında bu 2 test `SKIPPED` olarak işaretlenir (hata değil), geri kalan 16 test sorunsuz çalışır.

Gerçek proje dosyasıyla test etmek için, `MainScreen.4DGenie` dosyasını proje kök dizinine (tools/ ve tests/ klasörleriyle aynı seviyeye) yerleştirip testleri tekrar çalıştırmanız yeterlidir.

Testler şunları kapsar:
- Alias'ların doğru okunması
- Form / UserButton alias'larının doğru macro'ya dönüşmesi
- camelCase ve boşluklu alias normalizasyonu
- Duplicate alias / duplicate index tespiti
- Alias'sız objelerin raporlanması (`--strict` modda hataya dönüşmesi)
- Determinizm (aynı proje iki kez çalıştırılınca aynı header oluşması)
- Üretilen header'ın hem C hem C++ derleyicisiyle sorunsuz derlenmesi
