# Yerel başlangıç incelemesi — 3 Ekim 2026

Branch: feature/sources-update; başlangıç commit'i: 73c5134.

## Düzeltme durumu — fix/pipeline-reliability

İlk incelemedeki dört hata düzeltildi; testler artık xfail olmadan çalışıyor.
22 test geçti. Servisler arası HTTP sözleşmeleri de ASGI transport ile
öneri isteğinden kaynaklı yanıta kadar test edildi (LLM sahte, Qdrant bellek içi). Ek testler sayfalama, HTTP hata yanıtı, indeks yayınlama/okuma,
yeni indekse geçiş ve başarısız indekslemede eski verinin korunmasını kapsıyor.
Ingestion tüm bölüm metinlerini, linkleri, kaynak URL'sini ve metadata'yı koruyor.
Koleksiyon silme kaldırıldı; alias üzerinden güvenli yayın eklendi.
Kurulum için README ve dolu .env.example eklendi.

Aşağıdaki inceleme önceki durumun kaydıdır. Canlı scraping, gerçek OpenAI,
Docker ve tarayıcı uçtan uca doğrulaması hâlâ yapılmadı.

## Sonuç

MVP için servis sorumlulukları mantıklı: scraping/ingestion → Qdrant → matching + RAG → orchestration → frontend. Baştan yazım gerekmiyor. Ancak veri sözleşmesi, hata davranışı ve çalıştırma düzeni henüz güvenilir bir uçtan uca sistem oluşturmuyor.

## Çalıştırılan kontroller

- Python 3.11 ortamı: `.venv311`. Sistemdeki varsayılan Python 3.9 yerine proje Dockerfile'larıyla aynı ana sürüm kullanıldı.
- Python kaynaklarının tamamı compileall ile sözdizimi kontrolünden geçti.
- `tests/test_smoke.py`: 10 başarılı kontrol, bilinen hataları yeniden üreten 4 strict xfail. Xfail başarı anlamına gelmez; düzeltildiğinde işaret kaldırılmalıdır.
- Gerçek FastAPI TestClient: üç servis /health; iki yerel chat niyeti; eksik öneri isteği reddi.
- Profil doğrulama: negatif çalışan, negatif ciro, boş ihtiyaç reddi.
- Scraping: sabit HTML tablosundaki destek yüzdesinin korunması.
- Qdrant: gerçek qdrant-client bellek içi veritabanında sentetik vektör ve kayıtlarla test. Docker Qdrant sunucusu değildir.
- LLM: sahte istemciyle kesinti senaryosu. Gerçek embedding veya LLM API çağrısı yapılmadı.

Tekrar çalıştırma (repo kökünde):

```sh
.venv311/bin/python -m pytest -q -rx
# Bilinen sorunları normal başarısız test olarak göster:
.venv311/bin/python -m pytest -q --runxfail --tb=short
```

Test ortamının paket sürümleri `tests/requirements-baseline.txt` içinde. Bu, macOS/Python 3.11 test ortamının kaydıdır; tüm üretim servislerinin onaylanmış lock dosyası değildir.

## Testle doğrulanan sorunlar

1. **Scraper → ingestion bağlantısı:** runner.py `project/services/data/programs.json` yazar; ingestion main.py `project/services/ingestion_service/data/output.json` okur. Yeni kazınan veri otomatik indekslenmez.
2. **Adlandırılmış vektör araması:** ingestion `text-dense` vektörüyle yapılandırılmıştır. retrieval.py query_points çağrısında `using` belirtmez. İsimli koleksiyonda sorgu hata verir ve hata boş kaynak listesine çevrilir.
3. **Tekrarlı programlar:** matcher Qdrant chunk kayıtlarının her birini ayrı program olarak döndürür. Aynı program birden fazla öneri slotunu doldurabilir.
4. **Yanıltıcı başarı:** öneri üretiminde tüm LLM çağrıları hata verse bile genel önerilerle `success=True` döner. Kullanıcı teknik kesintiyi göremez.

## Kod incelemesindeki ek bulgular

- Ingestion mevcut koleksiyonu yeni indeksleme tamamlanmadan siler (`main.py:138`). Hata anında eski veri de kaybolabilir. Bu işlem çalıştırılmadı.
- Scraping metninin yalnız belirli başlıklara uyan bölümleri ingestion'a aktarılır. Diğer başlıklar ve linkler kaybolabilir. Metadata'da `source_url`, güncellik ve yapılandırılmış uygunluk koşulları taşınmıyor.
- Matching yalnız ilk scroll sayfasını okur; devam imlecini kullanmaz. Aday kapsamı top_k ile değişir. Kurallar çoğunlukla puanlama yapar; kesin uygunluk filtresi değildir.
- Async RAG fonksiyonu senkron Qdrant istemcisi çağırır; eşzamanlı isteklerde event loop'u bekletebilir.
- Model/koleksiyon adları çeşitli dosyalarda sabit; shared config ile tamamen yönetilmiyor. MIN_RETRIEVAL_SCORE aramaya uygulanmıyor.
- Health uçları yalnız uygulamanın cevap verdiğini gösterir; Qdrant, veri koleksiyonu veya OpenAI bağlantısını doğrulamaz.
- Docker Compose frontend'i başlatmıyor. Birden fazla index HTML sürümü var; aktif arayüz seçimi netleştirilmeli.
- Paketlerin çoğu sabitlenmemiş, Qdrant image latest. Yeniden kurulum davranışı zamanla değişebilir.
- README ve .env.example boş. Yerel kurulumda .env bulunmadığı için `docker compose config --quiet` başarısız.

## Henüz doğrulanmayanlar

Docker motoru çalışmıyor. Container build/start, gerçek Qdrant sunucu bağlantısı, canlı kurum sitelerinin güncel HTML'i, gerçek OpenAI embedding/cevap kalitesi, PDF ve tarayıcı uçtan uca akışı denenmedi. Testte kullanılan sahte API anahtarı gerçek çağrı için kullanılamaz. Bu inceleme tam sistemin çalıştığı iddiasında bulunmaz.

## Geliştirmeye hızlı geçiş sırası

1. Dört tekrarlanabilir hatayı, güvenli ingestion yazımını ve .env örneğini düzelt; testleri yeşile çevir. Mevcut servis sınırlarını koru.
2. Docker açıkken sentetik/ufak veriyle servisler arası sözleşme testini çalıştır. Program metadata'sı ile chunk kayıtlarının ayrımını netleştir.
3. Her kurumdan tek örnek sayfa kazı; başlık/metin/kaynak URL/güncellik alanlarını kontrol et. Küçük koleksiyonu gerçek embedding ile indeksle.
4. 5–10 sabit soru ve birkaç şirket profiliyle kaynak doğruluğunu, uygunluk davranışını ve maliyeti ölç. Ardından özellik geliştirmesine devam et.

Büyük bir test projesi kurmak gerekmiyor. Bağlantı ve hata senaryolarını kapsayan bu küçük set ile bir gerçek uçtan uca senaryo başlangıç için yeterli.
