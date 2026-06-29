# Teşvik Programı Scraper

## Kurulum

```bash
pip install -r requirements.txt
```

## Kullanım

```bash
# Tüm siteler
python main.py

# Tek site
python main.py --sites kosgeb

# Birden fazla site
python main.py --sites kosgeb tubitak

# Sadece URL'leri listele (sayfa çekme)
python main.py --dry-run

# Baştan başla (varolan output.json'u yok say)
python main.py --no-resume
```

## Çıktı: data/output.json

Her kayıt şu formatta:

```json
{
  "url": "https://...",
  "source": "kosgeb",
  "scraped_at": "2026-06-12T10:30:00+00:00",
  "program_name": "Girişim Sermayesi Yatırım Fonları Yatırımları",
  "sections": [
    {
      "title": "Programın Amacı",
      "content": "..."
    },
    {
      "title": "Başvuru Formları",
      "content": "...",
      "links": [
        { "text": "Başvuru Formu", "href": "https://..." }
      ]
    }
  ]
}
```

Hata olan kayıtlar `"error"` alanıyla saklanır — silinmez, tekrar çekilebilir.

## Proje yapısı

```
scraper/
├── main.py              # orchestrator, CLI
├── requirements.txt
├── data/
│   └── output.json      # çıktı (otomatik oluşur)
├── scrapers/
│   ├── kosgeb.py        # statik HTML, accordion yapısı
│   ├── tubitak.py       # Drupal 10, <strong> bölümleri
│   ├── tkdk.py          # IPARD, heading bazlı parse
│   └── teydeb.py        # TÜBİTAK sanayi kolu
└── utils/
    ├── http.py           # session, retry, rate limit
    └── models.py         # make_record, make_section
```

## Yeni site eklemek

1. `scrapers/yeni_site.py` oluştur
2. `get_program_urls(session)` ve `parse_program(session, url)` fonksiyonlarını yaz
3. `main.py`'deki `SCRAPERS` dict'ine ekle

```python
SCRAPERS = {
    "kosgeb":  kosgeb,
    "tubitak": tubitak,
    ...
    "yeni":    yeni_site,   # ekle
}
```
