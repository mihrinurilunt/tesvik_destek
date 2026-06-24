# Ingestion Service (Data Ingestion & Vectorization Pipeline)

Bu servis, **KOBİ Teşvik & Destek Sistemi** mimarisinde yer alan; scraper servisleri tarafından üretilen ham teşvik ve destek dökümanlarını işleyen, temizleyen, anlamsal parçalara bölen, embedding oluşturan ve sonuçları **Qdrant Vector Database** içerisine yükleyen bağımsız bir veri işleme mikroservisidir.

Sistem, veritabanına yalnızca doğrulanmış ve standartlaştırılmış verilerin yüklenmesini sağlamak amacıyla ortak veri sözleşmesi olan **ProgramDocument** modeli üzerinden doğrulama gerçekleştirir.

---

# İçindekiler

* [Proje Özeti](#-proje-özeti)
* [Teknolojik Altyapı](#-teknolojik-altyapı)
* [Üstlendiği Sorumluluklar](#-üstlendiği-sorumluluklar)
* [Mimari Yaklaşım](#-mimari-yaklaşım)
* [Proje Yapısı](#-proje-yapısı)
* [Veri İşleme Akışı](#-veri-işleme-akışı)
  * [1. Veri Yükleme](#1-veri-yükleme)
  * [2. Doğrulama](#2-doğrulama-validation)
  * [3. İçerik Temizleme](#3-içerik-temizleme)
  * [4. Chunking](#4-chunking)
  * [5. Embedding Oluşturma](#5-embedding-oluşturma)
  * [6. Qdrant'a Yükleme](#6-qdranta-yükleme)
* [Teknik Özellikler](#-teknik-özellikler)
* [Ortam Değişkenleri](#-ortam-değişkenleri-environment-variables)
* [Çalıştırma Talimatları](#-çalıştırma-talimatları)
  * [Docker ile Çalıştırma](#docker-ile-çalıştırma)
  * [Yerel Geliştirme](#yerel-geliştirme-local-development)
* [Yeni Veri Kaynağı Eklemek](#-yeni-veri-kaynağı-eklemek)
* [Gelecek Geliştirmeler](#-gelecek-geliştirmeler)

---

# Proje Özeti

Ingestion Service, farklı kurumların (KOSGEB, TÜBİTAK, TKDK, TEYDEB vb.) yayınladığı teşvik ve destek programlarını işleyerek, yapay zeka destekli semantik arama sistemlerinde kullanılabilecek yüksek kaliteli veri setleri üretmek amacıyla geliştirilmiştir.

Servis uçtan uca aşağıdaki işlemleri gerçekleştirir:

* Ham verilerin yüklenmesi
* Veri doğrulama (validation)
* İçerik temizleme (cleaning)
* Anlamsal parçalama (chunking)
* Embedding oluşturma
* Qdrant'a yükleme

Bu süreç sonucunda RAG sistemleri, semantic search servisleri ve LLM tabanlı soru-cevap sistemleri için hazır vektör veri altyapısı oluşturulur.

---

# Teknolojik Altyapı

Bu mikroservis aşağıdaki teknolojiler üzerine kuruludur:

* **Python**
* **Pydantic**
* **OpenAI Embedding API**
* **Qdrant Vector Database**
* **Docker**
* **FastAPI Shared Models**
* **HTTPX / Requests**

---

# Üstlendiği Sorumluluklar

Ingestion Service aşağıdaki temel görevleri yerine getirir:

## 1) Veri Doğrulama (Validation)

Scraper servislerinden gelen verilerin ortak veri sözleşmesine uygunluğunu kontrol eder.

## 2) İçerik Temizleme (Cleaning)

HTML etiketlerini, bozuk karakterleri ve gereksiz boşlukları temizler.

## 3) Chunking

Uzun dökümanları anlamsal olarak bölerek embedding üretimine hazır hale getirir.

## 4) Embedding Generation

OpenAI embedding modelleri kullanılarak vektör temsilleri oluşturur.

## 5) Vector Upload

Üretilen vektörleri Qdrant veritabanına yükler.

## 6) Duplicate Önleme

Aynı programın tekrar yüklenmesi durumunda upsert mantığı ile güncelleme gerçekleştirir.

---

# Mimari Yaklaşım

Servis klasik bir ETL (Extract → Transform → Load) veri işleme hattı olarak tasarlanmıştır.

## Akış Özeti

```text
Scrapers
    │
    ▼
Raw JSON Documents
    │
    ▼
Validation
    │
    ▼
Cleaning
    │
    ▼
Chunking
    │
    ▼
Embedding Generation
    │
    ▼
Qdrant Vector Database
````

## Avantajları

* Veri standardizasyonu sağlar
* Hatalı kayıtları engeller
* Semantic Search altyapısı oluşturur
* RAG sistemleriyle tam uyumludur
* Ölçeklenebilir veri işleme hattı sunar

---

# Proje Yapısı

```text
ingestion_service/

├── chunkers/
├── cleaners/
├── data/
├── embeddings/
├── loaders/
├── scrapers/
├── uploader/
├── utils/

├── main.py
├── Dockerfile
└── requirements.txt
```

---

# Veri İşleme Akışı

## 1. Veri Yükleme

Scraper servislerinden gelen JSON dosyaları okunur.

### Örnek Veri

```json
{
  "url": "https://example.com/program",
  "source": "kosgeb",
  "program_name": "Girişim Sermayesi Yatırım Fonları"
}
```

---

## 2. Doğrulama (Validation)

Tüm kayıtlar `ProgramDocument` modeli üzerinden doğrulanır.

Kontrol edilen alanlar:

* Program adı
* URL
* İçerik
* Tarihler
* Kaynak bilgisi

---

## 3. İçerik Temizleme

Cleaner katmanı aşağıdaki işlemleri uygular:

* HTML tag temizliği
* UTF düzeltmeleri
* Gereksiz boşluk temizliği
* Satır sonu normalizasyonu

### Örnek

```html
<p>Başvuru şartları...</p>
```

↓

```text
Başvuru şartları...
```

---

## 4. Chunking

Uzun içerikler anlamlı bölümlere ayrılır.

```text
Programın Amacı

↓
Chunk 1
Chunk 2
Chunk 3
```

Her chunk bağımsız olarak vektörleştirilir.

---

## 5. Embedding Oluşturma

Desteklenen modeller:

* `text-embedding-3-large`
* `text-embedding-3-small`

Her chunk embedding vektörüne dönüştürülür.

---

## 6. Qdrant'a Yükleme

Üretilen vektörler aşağıdaki koleksiyona kaydedilir:

```text
Collection : tesvikler_v2
Vector Name: text-dense
```

---

# Teknik Özellikler

## Ortak Model Doğrulaması

Tüm servisler aynı veri sözleşmesini kullanır:

```python
ProgramDocument
```

---

## Self-Healing Collection Reset

Servis açılışında koleksiyon şeması kontrol edilir.

Uyumsuzluk varsa otomatik yeniden oluşturulur.

---

## Upsert Mekanizması

```text
doc_id = program_id
```

Aynı kayıt tekrar işlendiğinde veri çoğaltılmaz.

---

## Sabit Vektör Alanı

```text
text-dense
```

Tüm servislerde ortak kullanılır.

---

# Ortam Değişkenleri (Environment Variables)

```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxx
QDRANT_URL=http://qdrant:6333

QDRANT_COLLECTION=tesvikler_v2
EMBEDDING_MODEL=text-embedding-3-small
```

---

# Çalıştırma Talimatları

## Docker ile Çalıştırma

### Build

```bash
docker compose --profile setup build --no-cache ingestion_service
```

### Run

```bash
docker compose run ingestion_service
```

> Servis varsayılan olarak otomatik başlatılmaz. Veri güvenliği amacıyla manuel çalıştırma tercih edilmiştir.

---

## Yerel Geliştirme (Local Development)

### Sanal Ortam Oluşturma

```bash
python -m venv .venv
```

### Aktivasyon

#### Windows

```bash
.venv\Scripts\activate
```

#### macOS / Linux

```bash
source .venv/bin/activate
```

### Bağımlılıkları Kurma

```bash
pip install -r requirements.txt
```

### Çalıştırma

```bash
python main.py
```

---

# Yeni Veri Kaynağı Eklemek

## 1. Yeni Scraper Dosyası Oluştur

```text
scrapers/yeni_site.py
```

## 2. Fonksiyonları Tanımla

```python
def get_program_urls(session):
    pass

def parse_program(session, url):
    pass
```

## 3. SCRAPERS Sözlüğüne Ekle

```python
SCRAPERS = {
    "kosgeb": kosgeb,
    "tubitak": tubitak,
    "tkdk": tkdk,
    "teydeb": teydeb,
    "yeni": yeni_site
}
```

---

# Özet

Ingestion Service, KOBİ Teşvik & Destek Sistemi içerisinde:

* Ham verileri standartlaştırır
* Veri kalitesini garanti eder
* Embedding üretir
* Vektör veritabanını besler
* Semantic Search ve RAG servisleri için gerekli veri altyapısını hazırlar

Bu sayede sistem genelinde güvenilir, ölçeklenebilir ve sürdürülebilir bir yapay zeka veri hattı oluşturulur.

# Lisans

* Bu proje KOBİ Teşvik & Destek Sistemi kapsamında geliştirilmiştir.

* Tüm hakları ilgili proje ekibine aittir.

```
```
