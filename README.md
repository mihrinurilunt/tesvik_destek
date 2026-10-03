# Teşvik Destek

Scraping/ingestion → Qdrant → matching + RAG → orchestration akışına sahip MVP.

## Yerel test

Python 3.11 kullanın. Repo kökünde:

```sh
python3.11 -m venv .venv311
.venv311/bin/pip install -r tests/requirements-baseline.txt
.venv311/bin/python -m pytest -q
```

Testler gerçek OpenAI çağrısı yapmaz. Qdrant bellek içinde, LLM/embedding kontrollü test yanıtlarıyla çalışır. Container ve canlı servis testi yerine geçmez.

## Docker ile çalıştırma

```sh
cd project
cp .env.example .env
# .env içindeki OPENAI_API_KEY değerini yerelde doldurun.
docker compose config --quiet
docker compose up -d --build qdrant
```

Önce veri hazırlayın. Scraper ile ingestion aynı `services/ingestion_service/data/output.json` dosyasını kullanır. İsterseniz repodaki örnek veriyle başlayabilirsiniz; bunun güncel olduğunu varsaymayın.

```sh
# Canlı kurum sayfalarından veri toplar:
docker compose --profile setup run --build --rm ingestion_service python -c "from runner import run_scrapers; print(run_scrapers(resume=False)['summary'])"
# OpenAI embedding kullanır ve yeni indeksi yayınlar:
docker compose --profile setup run --build --rm ingestion_service
# İndeks hazır olduğunda uygulama servisleri:
docker compose up -d --build matching_service rag_service orchestration_service
```

Scraping özetindeki hataları kontrol edin; hatalı kayıtlar ingestion'ı durdurur. Yenilemede `resume=False` kullanın; resume mevcut URL'leri atlar. Frontend Compose kapsamına dahil değildir; mevcut HTML sürümleri `project/frontend` altındadır.

## Eski Qdrant verisi ve güvenli güncelleme

Tüm servislerin aynı `.env` dosyasını kullanması gerekir. Örnekte `QDRANT_COLLECTION_NAME=tesvikler_live` seçilmiştir. Eski fiziksel `tesvikler_v2` koleksiyonu korunur. Yeni ingestion önce ayrı bir koleksiyonu tamamen oluşturup kayıt sayısını doğrular; ardından alias'ı atomik olarak yeni koleksiyona geçirir. Boş/geçersiz veri ya da indeksleme hatası mevcut hedefi değiştirmez.

Hedef isim fiziksel bir koleksiyonsa işlem açıklayıcı hatayla durur; otomatik silme/dönüştürme yapılmaz. Eski ve başarısız build koleksiyonları geri dönüş/inceleme için tutulur, zamanla yer kaplar. Temizlik ayrı bir bakım işlemidir. Aynı hedefe tek ingestion işi çalıştırın; eşzamanlı yayınlar için kilit henüz yok.

LLM veya retrieval kesintileri başarılı öneri gibi gösterilmez. `/health` yalnız servis canlılığıdır; harici bağlantıların hazır olduğunu kanıtlamaz.

İlk inceleme ve kalan işler: [LOCAL_REVIEW.md](LOCAL_REVIEW.md).

Son Docker ve canlı scraping kontrolünün kapsamı, düzeltmeler ve kalan kalite sorunları: [LIVE_SMOKE.md](LIVE_SMOKE.md).
