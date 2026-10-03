# Canlı küçük örnek testi — 3 Ekim 2026

## Doğrulananlar

- Dört Docker imajı başarıyla build edildi: ingestion, matching, RAG, orchestration.
- Ayrı `tesvik-smoke` Compose projesi ve veri volume'u oluşturuldu. Mevcut uygulama koleksiyonlarına dokunulmadı.
- Gerçek Qdrant `/healthz` ve matching `/health` HTTP 200 verdi.
- Üç kurumdan birer sayfa canlı olarak kazındı:
  - KOSGEB Girişimci Destek Programı: 6 bölüm, 15.575 metin karakteri.
  - TÜBİTAK 1000: 6 bölüm, 791 metin karakteri.
  - TKDK Çiftlik Faaliyetlerinin Çeşitlendirilmesi ve İş Geliştirme (302): 15 bölüm, 2.917 metin karakteri.
- Üç kayıt gerçek ingestion container'ında işlendi ve Qdrant `tesvik_smoke` alias'ı üzerinden yayınlandı.
- Embedding, bu aşamada **MockEmbedding(1536)** ile üretildi; ücretsiz ve deterministik bağlantı testidir. Bu koleksiyon gerçek anlamsal arama için kullanılamaz. Gerçek OpenAI embedding ile yeniden indekslenmelidir.
- Matching `/match` HTTP 200 ve üç ayrı program döndürdü.
- Yerel regresyon testleri: **29 geçti**.

## Canlı testte bulunan ve düzeltilenler

- TÜBİTAK kategori sayfaları programa karışıyordu. URL derinliği filtresi ve boş içerik kontrolü eklendi.
- TKDK dil değiştirme/hata sayfaları programa karışıyordu. Yalnız resmi `/Tedbir/` detayları seçiliyor; çalışmayan başlangıç adresleri kaldırıldı.
- HTTP 200 döndüren hata sayfaları URL ve başlık üzerinden reddediliyor.
- TKDK genel `Sektörler` başlığı yerine mevcut gezinme bağlantısındaki program adı alınıyor.
- KOSGEB'in uzun metadata'sı 1024 token chunk sınırını aşıyordu. Yapılandırılmış metadata Qdrant'ta korunuyor, fakat metin zaten belgeye dahil olduğundan embedding/LLM metnine tekrar eklenmiyor.

## Kalan önemli bulgu

Teknoloji / 5 çalışan / 100.000 ciro / Ar-Ge profiline üç program da 100 puan aldı. Bunların hedef kitleleri farklı. Bu test yalnız veri akışının çalıştığını kanıtlar; eşleştirme doğruluğunu kanıtlamaz.

Mevcut ingestion, alanlar bulunamadığında tüm sektör/ihtiyaçları varsayıyor; matching bilinmeyen çalışan/ciro sınırlarını uygun sayıyor. Hedef başvuru sahibi (şirket, üniversite, çiftçi vb.) yapılandırılmış filtre olarak kullanılmıyor. Bir sonraki kalite çalışması bu koşulları ve bilinmeyen değerleri modellemelidir.

## Henüz yapılmayanlar

OPENAI_API_KEY yerel `.env` içinde boştu. Gerçek embedding, LLM yanıtı, RAG/orchestration container çalışma testi, PDF ve tarayıcı akışı henüz doğrulanmadı. RAG ve orchestration için yalnız build doğrulandı.

## Yerel test ortamı

- Compose yapılandırması: `/tmp/tesvik-live-smoke-compose.yml` (geçici).
- Qdrant: `http://localhost:16333`; matching: `http://localhost:18001`.
- Örnekler ve kısa çıktı: `/tmp/tesvik-live-smoke/` (geçici).
- Proje adı: `tesvik-smoke`; kalıcı Docker volume: `tesvik-smoke_qdrant_storage`.
- Bu ortamın test embedding'lerini üretim verisiyle birleştirmeyin.
