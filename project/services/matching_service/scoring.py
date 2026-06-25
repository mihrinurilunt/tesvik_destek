"""
Scoring modülleri:
  - RuleBasedScorer  : Sektör / ciro / çalışan sayısı kriterlerini karşılaştırır. (ağırlık: 40%)
  - SemanticScorer   : Kullanıcı ihtiyaçları ↔ program amacı benzerliğini ölçer.  (ağırlık: 60%)
"""

from __future__ import annotations

import math
import re
from typing import List, Tuple

from schemas import ProgramData, UserProfile


# ---------------------------------------------------------------------------
# Rule-Based Scorer
# ---------------------------------------------------------------------------

class RuleBasedScorer:
    CRITERION_WEIGHTS = {
        "sector": 0.40,
        "revenue": 0.30,
        "employees": 0.30,
    }

    def score(self, profile: UserProfile, program: ProgramData) -> Tuple[float, List[str]]:
        reasons: List[str] = []
        weighted_score = 0.0

        # --- 1. Sektör ---
        sector_ok = self._check_sector(profile.sector, program.target_sectors)
        if sector_ok:
            weighted_score += self.CRITERION_WEIGHTS["sector"]
            if program.target_sectors:
                reasons.append(
                    f"Kullanıcı sektörü '{profile.sector}', programın hedef "
                    f"sektörleri ({', '.join(program.target_sectors)}) ile örtüşmektedir."
                )
            else:
                reasons.append("Program tüm sektörlere açık olduğundan sektör kriteri karşılanmaktadır.")

        # --- 2. Ciro ---
        if profile.annual_revenue is not None:
            rev_ok = self._in_range(profile.annual_revenue, program.min_revenue, program.max_revenue)
            if rev_ok:
                weighted_score += self.CRITERION_WEIGHTS["revenue"]
                reasons.append(
                    f"Kullanıcının yıllık cirosu ({profile.annual_revenue:,.0f} TL), "
                    f"programın ciro koşulları [{program.min_revenue or '-'} – "
                    f"{program.max_revenue or '-'} TL] aralığında yer almaktadır."
                )
        else:
            weighted_score += self.CRITERION_WEIGHTS["revenue"] * 0.5

        # --- 3. Çalışan sayısı ---
        if profile.employee_count is not None:
            emp_ok = self._in_range(profile.employee_count, program.min_employees, program.max_employees)
            if emp_ok:
                weighted_score += self.CRITERION_WEIGHTS["employees"]
                reasons.append(
                    f"Çalışan sayısı ({profile.employee_count}), programın "
                    f"[{program.min_employees or '-'} – {program.max_employees or '-'}] "
                    f"çalışan koşulu ile uyumludur."
                )
        else:
            weighted_score += self.CRITERION_WEIGHTS["employees"] * 0.5

        return round(weighted_score, 4), reasons

    @staticmethod
    def _check_sector(user_sector: str, target_sectors: List[str]) -> bool:
        if not target_sectors:
            return True
        user_norm = user_sector.lower().strip()
        return any(user_norm in t.lower() or t.lower() in user_norm for t in target_sectors)

    @staticmethod
    def _in_range(value: float, lo, hi) -> bool:
        if lo is not None and value < lo:
            return False
        if hi is not None and value > hi:
            return False
        return True


# ---------------------------------------------------------------------------
# Türkçe NLP yardımcıları
# ---------------------------------------------------------------------------

_STOPWORDS_TR = {
    "ve", "veya", "ile", "için", "bu", "bir", "da", "de", "den", "dan",
    "en", "ne", "ki", "mi", "mu", "mü", "ya", "olan", "gibi", "çok",
    "daha", "her", "hem", "ise", "hiç", "kadar", "olarak", "kendi",
    "biz", "siz", "onlar", "ben", "sen", "bunu", "bunun", "tarafından",
    "olan", "olup", "olan", "ile", "aracılığıyla", "üzerinden",
}

# Türkçe kelime kökleri — yaygın ek kalıpları soyulur
_TR_SUFFIXES = [
    "ları", "leri", "ların", "lerin", "lara", "lere", "lardan", "lerden",
    "ların", "lerin", "nın", "nin", "nun", "nün", "nda", "nde", "ndan", "nden",
    "ması", "mesi", "mak", "mek", "arak", "erek", "ıyor", "iyor", "uyor", "üyor",
    "acak", "ecek", "ıldı", "ildi", "uldu", "üldü", "tırma", "tirme",
    "laştır", "leştir", "laşma", "leşme", "ımı", "imi", "umu", "ümü",
    "sel", "sal", "lik", "lık", "luk", "lük", "cı", "ci", "cu", "cü",
    "çı", "çi", "çu", "çü", "sı", "si", "su", "sü", "da", "de", "ta", "te",
    "dan", "den", "tan", "ten", "dır", "dir", "dur", "dür", "tır", "tir",
    "lar", "ler", "ın", "in", "un", "ün", "ım", "im", "um", "üm",
    "ma", "me", "an", "en", "ı", "i", "u", "ü",
]

# Eş anlamlı / ilgili kelime grupları — birini görünce hepsini ekle
_SYNONYM_GROUPS = [
    {"hibe", "destek", "fon", "finansman", "teşvik", "yardım", "grant"},
    {"arge", "ar-ge", "araştırma", "geliştirme", "inovasyon", "yenilik", "rnd"},
    {"vergi", "muafiyet", "indirim", "istisna", "teşvik"},
    {"kobi", "küçük", "orta", "işletme", "şirket", "firma", "girişim"},
    {"yazılım", "teknoloji", "bilişim", "dijital", "yazilim", "tech", "it"},
    {"ihracat", "dış", "uluslararası", "global", "yurt"},
    {"üretim", "imalat", "sanayi", "fabrika", "tesis"},
    {"istihdam", "çalışan", "personel", "eleman", "işçi"},
    {"patent", "fikri", "mülkiyet", "telif", "buluş"},
    {"eğitim", "kurs", "sertifika", "öğrenim", "yetişkin"},
    {"enerji", "yenilenebilir", "güneş", "rüzgar", "çevre"},
    {"tarım", "hayvancılık", "gıda", "toprak", "çiftçi"},
    {"turizm", "otel", "konaklama", "seyahat"},
    {"sağlık", "medikal", "tıp", "hastane", "ilaç"},
]


def _stem_tr(word: str) -> str:
    """Basit kural tabanlı Türkçe kök bulma — en uzun eşleşen eki soy."""
    if len(word) <= 3:
        return word
    # Uzundan kısaya sırala ki en spesifik ek önce denensin
    for suffix in sorted(_SUFFIXES_SORTED, key=len, reverse=True):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: len(word) - len(suffix)]
    return word

_SUFFIXES_SORTED = _TR_SUFFIXES  # alias


def _expand_synonyms(tokens: List[str]) -> List[str]:
    """Token listesine eş anlamlıları ekle."""
    expanded = list(tokens)
    token_set = set(tokens)
    for group in _SYNONYM_GROUPS:
        if token_set & group:  # gruptaki herhangi bir kelime varsa
            expanded.extend(group - token_set)  # grubun geri kalanını ekle
    return expanded


def _normalize_tr(text: str) -> str:
    """Türkçe karakter normalizasyonu — büyük/küçük ve yaygın varyantlar."""
    text = text.lower()
    # Türkçe karakter → ASCII eşdeğeri (karşılaştırma için)
    replacements = {
        "ğ": "g", "ü": "u", "ş": "s", "ı": "i", "ö": "o", "ç": "c",
        "â": "a", "î": "i", "û": "u",
        # Yaygın yazım varyantları
        "ar-ge": "arge", "r&d": "arge", "rnd": "arge",
        "kobi": "kobi", "k.o.b.i": "kobi",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def _tokenize(text: str) -> List[str]:
    """Metni normalize et, tokenize et, stopword'leri çıkar, kök bul, eş anlamlıları genişlet."""
    normalized = _normalize_tr(text)
    # Özel birleşik terimleri koru (ar-ge → arge)
    normalized = re.sub(r"ar[\s\-]ge", "arge", normalized)
    
    tokens = re.findall(r"[a-z0-9]+", normalized)
    
    # Stopword filtrele
    tokens = [t for t in tokens if t not in _STOPWORDS_TR and len(t) > 2]
    
    # Kök bul
    tokens = [_stem_tr(t) for t in tokens]
    
    # Eş anlamlıları genişlet
    tokens = _expand_synonyms(tokens)
    
    return tokens


def _tf(tokens: List[str]) -> dict:
    freq: dict = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    total = len(tokens) or 1
    return {k: v / total for k, v in freq.items()}


def _cosine(vec_a: dict, vec_b: dict) -> float:
    keys = set(vec_a) & set(vec_b)
    dot = sum(vec_a[k] * vec_b[k] for k in keys)
    mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# Semantic Scorer
# ---------------------------------------------------------------------------

class SemanticScorer:
    """
    Türkçe NLP pipeline ile geliştirilmiş semantik benzerlik:
      1. Türkçe karakter normalizasyonu
      2. Kural tabanlı kök bulma (suffix stripping)
      3. Eş anlamlı kelime genişletme (synonym expansion)
      4. TF-ağırlıklı cosine similarity
    """

    def score(self, profile: UserProfile, program: ProgramData) -> Tuple[float, List[str]]:
        needs_text = " ".join(profile.needs) if isinstance(profile.needs, list) else profile.needs
        tokens_user = _tokenize(needs_text)
        tokens_prog = _tokenize(program.purpose)

        tf_user = _tf(tokens_user)
        tf_prog = _tf(tokens_prog)

        similarity = _cosine(tf_user, tf_prog)
        semantic_score = round(min(similarity * 1.5, 1.0), 4)  # boost + cap

        reasons: List[str] = []
        if semantic_score >= 0.5:
            reasons.append(
                f"Kullanıcı ihtiyaçları ile program amacı arasında yüksek "
                f"semantik benzerlik tespit edilmiştir (skor={semantic_score:.2f})."
            )
        elif semantic_score >= 0.25:
            reasons.append(
                f"Kullanıcı ihtiyaçları ile program amacı arasında orta düzeyde "
                f"semantik örtüşme bulunmaktadır (skor={semantic_score:.2f})."
            )
        else:
            reasons.append(
                f"Kullanıcı ihtiyaçları ile program amacı arasında sınırlı "
                f"semantik benzerlik mevcuttur (skor={semantic_score:.2f})."
            )

        return semantic_score, reasons