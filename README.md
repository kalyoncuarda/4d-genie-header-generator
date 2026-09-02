# 4D Systems Genie C Header Generator

4D Systems ViSi-Genie (.4DGenie) proje dosyalarını ayrıştırarak deterministik, standartlara uygun C/C++ başlık (`.h`) dosyaları üreten bir CLI aracıdır.

## 🚀 Özellikler

- **Deterministik Çıktı:** Bileşenleri tip ve index sırasına göre sıralar.
- **İsim Normalizasyonu:** Alias metinlerini C makro standartlarına (`UPPER_SNAKE_CASE`) dönüştürür.
- **Hata Kontrolleri:** Mükerrer index veya çakışan makro isimlerini otomatik yakalar.
- **Format Doğrulama:** Büyük/küçük harf farklarını tolere eder; bilinmeyen bir obje tipi veya `Name` alanından index çıkarılamayan bir obje ile karşılaşırsa objeyi atlayıp nedenini açıklayan bir uyarı basar (sessizce yanlış veri üretmez).
- **Strict Mode (`--strict`):** Alias verilmemiş bileşenler olduğunda hata fırlatır.
- **Check Mode (`--check`):** Header dosyasının güncel olup olmadığını dosyayı değiştirmeden doğrular (CI uyumlu).

## 🛠️ Desteklenen Bileşenler

- Form / Menüler (`FORM_...`)
- Butonlar (`USERBUTTON_...`, `WINBUTTON_...`)
- Metin Nesneleri (`STRINGS_...`, `STATICTEXT_...`)
- Görseller & Klavyeler (`USERIMAGES_...`, `IMAGE_...`, `KEYBOARD_...`)
- Medya & Çizimler (`VIDEO_...`, `SOUNDS_...`, `PANEL_...`, `BORDER_...`)

## ➕ Yeni Bir Genie Obje Tipi Eklenirse Ne Yapılmalı

4D Studio üzerinde projeye, script'in şu an bilmediği yeni bir obje tipi (örn. `Gauge`, `Led`, `Slider`) eklenirse, script bunu **otomatik olarak eklemez**. Bunun yerine terminalde şuna benzer bir uyarı basar ve o objeyi header'a yazmadan atlar:

```
WARNING: Unrecognized block type 'Gauge' at line 5496. If this is a new Genie object type, register it with: --add-type Gauge. Skipped.
```

Desteklenen obje tipleri artık kaynak kodun (`.py` dosyasının) içinde **değil**, script ile aynı klasördeki **`genie_types.json`** dosyasında tutuluyor. Yeni bir tip eklemenin 2 geçerli yolu var:

### Yöntem 1 — CLI ile (önerilen)

```bash
python3 tools/generate_genie_header.py --add-type Gauge
```

Bu komut, `genie_types.json`'a `Gauge` tipini otomatik olarak ekler (başlık olarak tip adının kendisini kullanır, listenin sonuna ekler). Hangi tiplerin şu an kayıtlı olduğunu görmek için:

```bash
python3 tools/generate_genie_header.py --list-types
```

### Yöntem 2 — `genie_types.json`'ı elle düzenleme

`genie_types.json`, düz bir metin/JSON dosyası olduğu için istersen doğrudan bir editörle de açıp yeni bir satır ekleyebilirsin:

```json
{
  "Form": "Forms / Menus",
  "UserButton": "User Buttons",
  ...
  "Gauge": "Gauges"
}
```
Sözlükteki **sıra**, header'daki bölümlerin sırasını da belirliyor — yeni tipi istediğin yere (örn. iki tip arasına) ekleyebilirsin.

### ⚠️ Önemli: Kaynak koddaki `DEFAULT_TYPES`'ı elle değiştirmek İŞE YARAMAZ

`generate_genie_header.py` dosyasının içinde bir `DEFAULT_TYPES` sözlüğü var — ama bu, **sadece `genie_types.json` hiç yokken**, ilk çalıştırmada dosyayı oluşturmak için kullanılan bir "tohum" değer. `genie_types.json` bir kez oluştuktan sonra, script **artık kod içindeki `DEFAULT_TYPES`'a hiç bakmaz** — sadece JSON dosyasını okur. Yani kaynak kodu elle değiştirip yeni tip eklemeye çalışmak, `genie_types.json` zaten varsa **hiçbir etki yapmaz**. Yeni tip eklemek için her zaman Yöntem 1 ya da Yöntem 2'yi kullan.

Değişiklikten sonra script'i tekrar çalıştırıp testleri (`python3 -m pytest tests/ -v`) tekrar geçtiğinden emin ol.

## ⚠️ Diğer Otomatik Uyarılar

Script, aşağıdaki durumlarda da objeyi header'a yazmadan atlar ve terminalde nedenini açıklayan bir `WARNING` basar:

- **Bilinmeyen obje tipi:** `.4DGenie`'de `GENIE_TYPES`'ta tanımlı olmayan bir blok görülürse (yukarıdaki bölüme bakın).
- **`Name` alanından index çıkarılamıyor:** 4D Studio her objeye normalde `TipAdıSayı` formatında bir isim verir (örn. `UserButton5`, `Form2`). Eğer bir objenin `Name` değeri sayı ile bitmiyorsa (örn. elle düzenleme sonucu bozulmuşsa), script index'i güvenilir şekilde belirleyemez ve şu formatta uyarır:
  ```
  WARNING: Could not extract index from Name 'ConnectButton' (UserButton) at line 12 - reason: 'Name' does not end with a number (expected format like 'UserButton5', got 'ConnectButton'). Object skipped.
  ```
  Bu durumda ilgili objeyi 4D Studio'da kontrol edip `Name` alanının bozulmadığından emin olman gerekir.

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
