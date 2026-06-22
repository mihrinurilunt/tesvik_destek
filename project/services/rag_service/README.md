# 🎯 RAG Service (Retrieval-Augmented Generation)

Bu servis, **KOBİ Teşvik & Destek Sistemi** mimarisinde yer alan; eşleşen hibe programları hakkında **resmî dökümanlara dayalı anlamsal arama** yapan ve **yapay zeka destekli akıllı yanıtlar** üreten bağımsız bir **FastAPI mikroservisidir**.

Sistem, yapay zekanın **uydurma (hallucination)** bilgi üretmesini engellemek amacıyla **Retrieval-Augmented Generation (RAG)** mimarisini kullanır. Üretilen yanıtlar yalnızca **Qdrant Vektör Veritabanı** içerisinde bulunan **doğrulanmış resmî belgeler** ile sınırlandırılır.

---

# 📌 İçindekiler

* [Proje Özeti](#-proje-özeti)
* [Teknolojik Altyapı](#-teknolojik-altyapı)
* [Sorumluluklar](#-üstlendiği-sorumluluklar)
* [Mimari Yaklaşım](#-mimari-yaklaşım)
* [Ortam Değişkenleri](#-ortam-değişkenleri-environment-variables)
* [API Uç Noktaları](#-api-uç-noktaları-endpoints)

  * [1. Health Check](#1-health-check)
  * [2. Streaming Chat](#2-streaming-chat)
  * [3. Structured Guide Generation](#3-structured-guide-generation)
* [Çalıştırma Talimatları](#-çalıştırma-talimatları)

  * [Docker ile Çalıştırma](#docker-ile-çalıştırma-önerilen)
  * [Yerel Geliştirme Modu](#yerel-geliştirme-local-development)
* [Swagger / API Dokümantasyonu](#-swagger--api-dokümantasyonu)

---

# 📖 Proje Özeti

RAG Service, kullanıcıların belirli bir teşvik / destek programı hakkında sordukları soruları, ilgili programın **resmî başvuru rehberleri**, **uygulama esasları** ve diğer doğrulanmış dökümanlar üzerinden yanıtlamak için geliştirilmiştir.

Servis iki temel kullanım senaryosu sunar:

* **Canlı sohbet (streaming chat):** Kullanıcının sorduğu soruya, seçili programın dökümanlarını referans alarak akış halinde yanıt üretir.
* **Yapılandırılmış rehber üretimi:** Seçilen programın resmî belgelerini analiz ederek sistem genelinde kullanılan veri sözleşmesine uygun, temiz ve yapılandırılmış JSON çıktısı üretir.

---

# 🛠️ Teknolojik Altyapı

Bu mikroservis aşağıdaki teknolojiler üzerine kuruludur:

* **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/)
  Asenkron ve yüksek performanslı API altyapısı sağlar.

* **RAG Framework:** [LlamaIndex](https://www.llamaindex.ai/)
  Döküman yönetimi, indeksleme ve sorgu motoru katmanında kullanılır.

* **Vector Database Client:** [Qdrant Client](https://qdrant.tech/)
  Vektör tabanlı benzerlik araması ve metadata filtreleme işlemlerini yönetir.

* **LLM & Embedding:** [OpenAI API](https://openai.com/)

  * `gpt-4o-mini` → cevap üretimi
  * `text-embedding-3-small` → embedding oluşturma

* **ASGI Sunucusu:** [Uvicorn](https://www.uvicorn.org/)
  FastAPI uygulamasını çalıştırmak için kullanılır.

---

# 📋 Üstlendiği Sorumluluklar

RAG Service aşağıdaki temel görevleri yerine getirir:

## 1) Anlamsal Arama (Semantic Retrieval)

Qdrant veritabanındaki `tesvikler_v2` koleksiyonu üzerinde, `text-dense` vektör alanı kullanılarak anlamsal benzerlik araması yapılır.

## 2) Metadata Filtreleme

Sorgular yalnızca kullanıcının seçtiği hibe / destek programına ait belgelerle sınırlandırılır. Bunun için `program_adi` metadata alanı üzerinden filtreleme uygulanır.

## 3) Canlı Akış (Streaming Chat)

Kullanıcı sorularına OpenAI destekli, gerçek zamanlı ve akış (streaming) biçiminde yanıt üretir.

## 4) Yapılandırılmış Rapor Üretimi

Resmî belgeleri tarayarak sistem genelinde tanımlanmış API sözleşmesine uygun `ProgramDocument` formatında JSON çıktısı oluşturur.

---

# 🧠 Mimari Yaklaşım

Servis, klasik bir “LLM’ye doğrudan soru sor” yaklaşımı yerine **RAG (Retrieval-Augmented Generation)** mimarisi kullanır.

## Akış Özeti

1. Kullanıcı bir **program adı** ve isteğe bağlı olarak bir **soru** gönderir.
2. Sistem önce ilgili program adına göre Qdrant üzerinde **metadata filtrelemesi** yapar.
3. Ardından sadece o programa ait belgeler arasında **anlamsal benzerlik araması** gerçekleştirilir.
4. Elde edilen ilgili belge parçaları (context), LLM’e bağlam olarak verilir.
5. LLM yalnızca bu doğrulanmış içeriklere dayanarak yanıt üretir.

## Avantajları

* **Hallucination riskini azaltır**
* **Yanıtların resmî kaynaklara dayanmasını sağlar**
* **Program bazlı filtreleme ile doğruluk ve performansı artırır**
* **Geniş döküman havuzlarında ölçeklenebilir arama altyapısı sunar**

---

# ⚙️ Ortam Değişkenleri (Environment Variables)

Servisin çalışabilmesi için `.env` dosyasında aşağıdaki değişkenlerin tanımlı olması gerekir:

```env
OPENAI_API_KEY=sk-proj-YourActualOpenAIKeyHere
QDRANT_URL=http://qdrant:6333
```

## Açıklamalar

* **OPENAI_API_KEY**
  OpenAI tabanlı LLM ve embedding servislerine erişim için kullanılır.

* **QDRANT_URL**
  Qdrant vektör veritabanısının servis adresidir. Docker ağı içinde genellikle `http://qdrant:6333` şeklinde tanımlanır.

---

# 🚀 API Uç Noktaları (Endpoints)

## 1. Health Check

Servisin çalışır durumda olup olmadığını ve temel bağlantı durumunu kontrol etmek için kullanılır.

* **Method:** `GET`
* **Path:** `/health`

### Örnek İstek

```http
GET /health
```

### Örnek Yanıt

```json
{
  "status": "healthy",
  "service": "rag_service"
}
```

---

## 2. Streaming Chat

Kullanıcının seçtiği destek programına ait dökümanları baz alarak **canlı akış (streaming)** şeklinde sohbet yanıtı üretir.

* **Method:** `POST`
* **Path:** `/chat`

### İstek Gövdesi

```json
{
  "message": "Girişimci desteğine 4 yaşında bir şirket başvurabilir mi?",
  "program_name": "Girişimci Destek Programı"
}
```

### Alan Açıklamaları

* **message**
  Kullanıcının sorduğu soru veya doğal dil girdisi

* **program_name**
  Sorgunun sınırlandırılacağı destek / hibe programı adı

### Yanıt Türü

Bu endpoint klasik JSON yerine **`text/plain` formatında streaming response** döndürür.
Yanıt, kullanıcı arayüzünde parça parça (token/token veya cümle/cümle) gösterilebilir.

### Örnek Kullanım Senaryosu

* Kullanıcı belirli bir program seçer
* Soruyu gönderir
* Sistem yalnızca o programın resmî dökümanlarını tarar
* Yanıt akış halinde kullanıcıya iletilir

---

## 3. Structured Guide Generation

Seçili programın resmî dökümanlarını analiz ederek, sistem genelinde kullanılan veri sözleşmesine uygun **yapılandırılmış başvuru rehberi** üretir.

* **Method:** `POST`
* **Path:** `/generate`

### İstek Gövdesi

```json
{
  "program_name": "Girişimci Destek Programı"
}
```

### Yanıt

Bu endpoint, ilgili programın resmî dökümanlarından türetilmiş, temizlenmiş ve yapılandırılmış bir JSON çıktısı döndürür.
Çıktı, sistem genelinde kullanılan **`ProgramDocument`** şemasına uygun olacak şekilde tasarlanır.

### Örnek Yanıt Yapısı

> Not: Aşağıdaki örnek şema temsilidir. Gerçek alanlar sizin API sözleşmenize göre değişebilir.

```json
{
  "program_name": "Girişimci Destek Programı",
  "summary": "Programın amacı ve kapsamı...",
  "application_conditions": [
    "Başvuru sahibi KOBİ statüsünde olmalıdır.",
    "Belirli sektörlerde faaliyet gösteriyor olmalıdır."
  ],
  "support_items": [
    {
      "title": "Kuruluş Desteği",
      "amount": "X TL"
    }
  ],
  "important_dates": [
    {
      "label": "Son Başvuru Tarihi",
      "value": "2026-12-31"
    }
  ]
}
```

---

# 💻 Çalıştırma Talimatları

## Docker ile Çalıştırma (Önerilen)

Mikroservis mimarisinde, servislerin birlikte ayağa kaldırılması için Docker Compose kullanılması önerilir.

Projenin kök dizininde aşağıdaki komutu çalıştırın:

```bash
docker compose up -d --build
```

Sistemi başlatın:

```bash
docker compose up -d
```

## Bu komut ne yapar?

* İlgili Docker image’larını oluşturur
* Servisleri arka planda başlatır
* RAG servisini diğer bağımlı servislerle aynı ağ içinde ayağa kaldırır

---

## Yerel Geliştirme (Local Development)

Yerel bilgisayarınızda geliştirme / test amacıyla servisi çalıştırmak için aşağıdaki adımları izleyin.

## 1) Sanal ortamı aktive edin

Örnek:

### Windows

```bash
venv\Scripts\activate
```

### macOS / Linux

```bash
source venv/bin/activate
```

## 2) Bağımlılıkları yükleyin

```bash
pip install -r requirements.txt
```

## 3) Ortam değişkenlerini tanımlayın

Proje dizininde `.env` dosyası oluşturup aşağıdaki değerleri girin:

```env
OPENAI_API_KEY=sk-proj-YourActualOpenAIKeyHere
QDRANT_URL=http://localhost:6333
```

> Eğer Qdrant’ı Docker içinde ayrı bir servis olarak çalıştırıyorsanız URL buna göre değişebilir.

## 4) Servisi başlatın

```bash
uvicorn main:app --host 127.0.0.1 --port 8002 --reload
```

### Parametreler

* **main:app** → FastAPI uygulamasının bulunduğu modül ve app nesnesi
* **--host 127.0.0.1** → Servisi yerel makinede yayınlar
* **--port 8002** → Uygulamanın dinleyeceği port
* **--reload** → Kod değişikliklerinde otomatik yeniden başlatma sağlar

---

# 📚 Swagger / API Dokümantasyonu

Servis çalıştıktan sonra interaktif API dokümantasyonuna aşağıdaki adres üzerinden erişebilirsiniz:

```bash
http://localhost:8002/docs
```

Bu arayüz üzerinden:

* endpoint’leri test edebilir,
* request body örneklerini görebilir,
* yanıt formatlarını inceleyebilir,
* geliştirme sürecinde hızlı doğrulama yapabilirsiniz.

---

# Qdrant veritabanını kontrol paneli

Tarayıcınızı açın ve şu adrese gidin: 

```bash
http://localhost:6333/dashboard
```

Sol menüdeki "Collections" sekmesine tıkladığınızda tesvikler_v2 adında bir koleksiyon görmelisiniz.

Bu koleksiyonun içine girdiğinizde, ingestion_service tarafından yüklenen verileri (noktaları/vektörleri) görüyorsanız veritabanınız çalışıyor ve doludur.
---

# 🧩 Örnek Kullanım Akışları

## Senaryo 1 — Kullanıcının program hakkında soru sorması

1. Kullanıcı arayüzden bir destek programı seçer.
2. “Şirketim bu programa başvurabilir mi?” gibi bir soru girer.
3. Frontend, `/chat` endpoint’ine istek atar.
4. RAG servisi:

   * ilgili programın dökümanlarını filtreler,
   * benzer içerikleri getirir,
   * LLM ile bağlamsal yanıt üretir,
   * yanıtı akış halinde döndürür.

## Senaryo 2 — Program rehberi oluşturulması

1. Kullanıcı bir program seçer.
2. Frontend, `/generate` endpoint’ine sadece `program_name` ile istek gönderir.
3. Servis, ilgili resmî belgeleri tarar.
4. Programın şartları, destek kalemleri, açıklamaları ve önemli bilgileri yapılandırılmış JSON olarak üretir.

---

# ✅ Özet

RAG Service, KOBİ Teşvik & Destek Sistemi içinde aşağıdaki kritik ihtiyacı çözer:

* Resmî dökümanlara dayalı **güvenilir bilgi erişimi**
* Belirli programlara özel **semantic search**
* Gerçek zamanlı **AI destekli sohbet deneyimi**
* Sistem geneline uygun **yapılandırılmış veri üretimi**

Bu sayede kullanıcılar, destek programları hakkında daha hızlı, daha doğru ve daha açıklanabilir bilgiye ulaşabilir.

---
