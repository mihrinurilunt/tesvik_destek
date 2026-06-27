from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Callable

from shared.enums import IntentType, TargetService
from shared.models import UserProfile
from shared.schemas import IntentResult


@dataclass(frozen=True)
class IntentRule:
    """
    Tek bir intent kuralını temsil eder.

    keywords:
        Mesaj içinde aranacak kelime/ifade listesi.

    intent:
        Eşleşirse dönecek IntentType.

    base_confidence:
        Bu kural eşleştiğinde verilecek başlangıç güven skoru.

    target_service:
        Bu intent sonucunda ana olarak hangi servis çağrılacak?
    """

    keywords: tuple[str, ...]
    intent: IntentType
    base_confidence: float
    target_service: TargetService
    needs_profile: bool = False


# Kısa ve net selamlaşmalar.
GREETING_KEYWORDS = (
    "merhaba",
    "selam",
    "slm",
    "iyi gunler",
    "iyi günler",
    "gunaydin",
    "günaydın",
    "iyi aksamlar",
    "iyi akşamlar",
)

# Sistem hakkında genel sorular.
GENERAL_INFO_KEYWORDS = (
    "sen kimsin",
    "ne ise yariyorsun",
    "ne işe yarıyorsun",
    "bu sistem ne",
    "sistem nasil calisir",
    "sistem nasıl çalışır",
    "nasil kullanilir",
    "nasıl kullanılır",
    "bana nasil yardimci olursun",
    "bana nasıl yardımcı olursun",
)

# Kullanıcı kendisine uygun destek/teşvik önerisi istiyor.
RECOMMENDATION_KEYWORDS = (
    "bana uygun",
    "uygun destek",
    "uygun tesvik",
    "uygun teşvik",
    "destek bul",
    "tesvik bul",
    "teşvik bul",
    "destek oner",
    "destek öner",
    "tesvik oner",
    "teşvik öner",
    "hangi destekler",
    "hangi tesvikler",
    "hangi teşvikler",
    "desteklerden yararlanabilir",
    "tesviklerden yararlanabilir",
    "teşviklerden yararlanabilir",
)

# Belge, şart, başvuru, süreç gibi doküman bilgisinden cevaplanması gereken sorular.
RAG_QUESTION_KEYWORDS = (
    "belge",
    "belgeler",
    "evrak",
    "evraklar",
    "sart",
    "şart",
    "sartlar",
    "şartlar",
    "kosul",
    "koşul",
    "kosullar",
    "koşullar",
    "basvuru",
    "başvuru",
    "nasil basvur",
    "nasıl başvur",
    "gerekli",
    "gerekiyor",
    "surec",
    "süreç",
    "adim",
    "adım",
    "limit",
    "tutar",
    "oran",
    "hibe",
    "geri odeme",
    "geri ödeme",
    "son tarih",
)

# Uygunluk soruları. Çoğu zaman Matching + RAG gerekir.
ELIGIBILITY_KEYWORDS = (
    "uygun muyum",
    "uygun olur muyum",
    "uygun mudur",
    "basvurabilir miyim",
    "başvurabilir miyim",
    "alabilir miyim",
    "yararlanabilir miyim",
    "faydalanabilir miyim",
    "hak kazanir miyim",
    "hak kazanır mıyım",
    "uygunluk",
    "sartlari sagliyor muyum",
    "şartları sağlıyor muyum",
)

# Kullanıcı profil bilgisini güncelliyor veya yeni profil bilgisi veriyor.
PROFILE_UPDATE_KEYWORDS = (
    "calisan sayimiz",
    "çalışan sayımız",
    "calisan sayisi",
    "çalışan sayısı",
    "sektorumuz",
    "sektörümüz",
    "sektor",
    "sektör",
    "ciromuz",
    "yillik ciro",
    "yıllık ciro",
    "gelirimiz",
    "sirketim",
    "şirketim",
    "firmam",
    "istanbul",
    "ankara",
    "izmir",
    "bursa",
    "kocaeli",
    "sakarya",
    "arge",
    "ar-ge",
    "ihracat",
    "dijital",
    "makine",
    "teçhizat",
    "techizat",
)

# Proje kapsamı dışı çok yaygın sorular.
OUT_OF_SCOPE_KEYWORDS = (
    "hava nasil",
    "hava nasıl",
    "film oner",
    "film öner",
    "dizi oner",
    "dizi öner",
    "yemek tarifi",
    "spor programi",
    "spor programı",
    "sarki oner",
    "şarkı öner",
    "oyun oner",
    "oyun öner",
    "matematik odevi",
    "matematik ödevi",
)

# Mesajda bunlardan biri varsa proje kapsamıyla ilişkili olabilir.
IN_SCOPE_KEYWORDS = (
    "tesvik",
    "teşvik",
    "destek",
    "hibe",
    "kosgeb",
    "tubitak",
    "tübitak",
    "ito",
    "ihracat",
    "arge",
    "ar-ge",
    "kobi",
    "basvuru",
    "başvuru",
    "belge",
    "evrak",
    "sart",
    "şart",
    "uygun",
)


def normalize_text(text: str) -> str:
    """
    Türkçe karakter ve büyük/küçük harf farkını azaltmak için metni normalize eder.
    Intent kuralları daha stabil çalışsın diye kullanılır.
    """

    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)

    replacements = {
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
    }

    for source, target in replacements.items():
        text = text.replace(source, target)

    text = re.sub(r"\s+", " ", text)
    return text


def contains_any(message: str, keywords: tuple[str, ...]) -> bool:
    normalized_keywords = tuple(normalize_text(keyword) for keyword in keywords)
    return any(keyword in message for keyword in normalized_keywords)


def keyword_score(message: str, keywords: tuple[str, ...]) -> float:
    """
    Eşleşen keyword sayısına göre küçük bir skor üretir.
    Amaç mükemmel NLP yapmak değil, rule-based intent için makul confidence vermek.
    """

    normalized_keywords = tuple(normalize_text(keyword) for keyword in keywords)
    matched_count = sum(1 for keyword in normalized_keywords if keyword in message)

    if matched_count == 0:
        return 0.0

    # Çok fazla keyword eşleşirse confidence biraz artsın ama 1'i geçmesin.
    return min(0.60 + matched_count * 0.08, 0.95)


def has_number(message: str) -> bool:
    return bool(re.search(r"\d+", message))


def has_profile_signal(message: str) -> bool:
    """
    Mesajda şirket profiline benzeyen bilgi var mı?
    Örnek:
        12 çalışanımız var
        İstanbul'dayız
        yazılım şirketiyiz
        yıllık ciro 3 milyon
    """

    profile_patterns = (
        r"\d+\s*(calisan|personel|kisi|kişi)",
        r"(ciro|gelir)\s*\d+",
        r"\d+\s*(milyon|bin|tl)",
        r"(limited|anonim|sahis|şahıs)",
    )

    if contains_any(message, PROFILE_UPDATE_KEYWORDS):
        return True

    return any(re.search(pattern, message) for pattern in profile_patterns)


def is_profile_complete(user_profile: UserProfile | None) -> bool:
    """
    Teşvik önerisi için minimum profil bilgisi var mı kontrol eder.
    UserProfile modeliniz required alanlarla geldiyse genelde True döner.
    """

    if user_profile is None:
        return False

    return bool(
        user_profile.sector
        and user_profile.employee_count is not None
        and user_profile.annual_revenue is not None
        and user_profile.needs
    )


def detect_intent(
    message: str,
    user_profile: UserProfile | None = None,
    *,
    use_llm_fallback: bool = False,
    llm_fallback: Callable[[str, UserProfile | None], IntentResult] | None = None,
) -> IntentResult:
    """
    Kullanıcı mesajını analiz eder ve IntentResult döndürür.

    MVP mantığı:
        1. Önce rule-based karar verir.
        2. Confidence düşükse UNKNOWN döner.
        3. İleride use_llm_fallback=True yapılırsa, emin olmadığı durumda LLM'e gidebilir.

    Bu fonksiyon cevap üretmez.
    Sadece orchestration_service'in hangi akışı çalıştıracağına karar verir.
    """

    normalized_message = normalize_text(message)

    if not normalized_message:
        return IntentResult(
            intent=IntentType.UNKNOWN,
            confidence=0.0,
            is_in_scope=False,
            needs_user_profile=False,
            target_service=TargetService.ORCHESTRATION,
            extracted_profile=None,
            missing_fields=[],
            reason="Boş mesaj gönderildi.",
        )

    # 1. Çok kısa selamlaşmalar direkt greeting.
    if normalized_message in {normalize_text(item) for item in GREETING_KEYWORDS}:
        return IntentResult(
            intent=IntentType.GREETING,
            confidence=0.98,
            is_in_scope=True,
            needs_user_profile=False,
            target_service=TargetService.ORCHESTRATION,
            extracted_profile=None,
            missing_fields=[],
            reason="Kullanıcı selamlaşma mesajı gönderdi.",
        )

    # 2. Açıkça kapsam dışı ama teşvik/destek kelimesi içermiyorsa out_of_scope.
    if contains_any(normalized_message, OUT_OF_SCOPE_KEYWORDS) and not contains_any(
        normalized_message,
        IN_SCOPE_KEYWORDS,
    ):
        return IntentResult(
            intent=IntentType.OUT_OF_SCOPE,
            confidence=0.90,
            is_in_scope=False,
            needs_user_profile=False,
            target_service=TargetService.ORCHESTRATION,
            extracted_profile=None,
            missing_fields=[],
            reason="Mesaj teşvik/destek sistemi kapsamı dışında görünüyor.",
        )

    # 3. Sistem hakkında genel soru.
    if contains_any(normalized_message, GENERAL_INFO_KEYWORDS):
        return IntentResult(
            intent=IntentType.GENERAL_INFO,
            confidence=0.88,
            is_in_scope=True,
            needs_user_profile=False,
            target_service=TargetService.ORCHESTRATION,
            extracted_profile=None,
            missing_fields=[],
            reason="Kullanıcı sistemin ne yaptığını veya nasıl çalıştığını soruyor.",
        )

    # 4. Uygunluk soruları önce yakalanmalı.
    # Çünkü 'uygun destek bul' ile 'uygun muyum' farklı şeylerdir.
    eligibility_confidence = keyword_score(normalized_message, ELIGIBILITY_KEYWORDS)
    if eligibility_confidence > 0:
        return IntentResult(
            intent=IntentType.ELIGIBILITY_QUESTION,
            confidence=eligibility_confidence,
            is_in_scope=True,
            needs_user_profile=not is_profile_complete(user_profile),
            target_service=TargetService.MATCHING,
            extracted_profile=None,
            missing_fields=get_missing_profile_fields(user_profile),
            reason="Kullanıcı bir desteğe uygun olup olmadığını soruyor.",
        )

    # 5. Kullanıcı mevcut profilini güncelliyor olabilir.
    # Eğer zaten profil varsa ve yeni sayı/şehir/sektör gibi bilgi veriyorsa PROFILE_UPDATE daha anlamlıdır.
    if user_profile is not None and has_profile_signal(normalized_message):
        return IntentResult(
            intent=IntentType.PROFILE_UPDATE,
            confidence=0.82,
            is_in_scope=True,
            needs_user_profile=False,
            target_service=TargetService.MATCHING,
            extracted_profile=None,
            missing_fields=[],
            reason="Kullanıcı mevcut profil bilgilerini güncelliyor gibi görünüyor.",
        )

    # 6. Kullanıcı kendisine uygun destekleri istiyor.
    recommendation_confidence = keyword_score(normalized_message, RECOMMENDATION_KEYWORDS)
    if recommendation_confidence > 0:
        return IntentResult(
            intent=IntentType.INCENTIVE_RECOMMENDATION,
            confidence=recommendation_confidence,
            is_in_scope=True,
            needs_user_profile=not is_profile_complete(user_profile),
            target_service=TargetService.MATCHING,
            extracted_profile=None,
            missing_fields=get_missing_profile_fields(user_profile),
            reason="Kullanıcı kendisine uygun teşvik/destek önerisi istiyor.",
        )

    # 7. Mesaj profil bilgisi içeriyor ve destek/teşvik bağlamı varsa öneri isteği olabilir.
    # Örnek: '12 çalışanlı yazılım şirketiyiz, ar-ge desteği arıyoruz'
    if has_profile_signal(normalized_message) and contains_any(normalized_message, IN_SCOPE_KEYWORDS):
        return IntentResult(
            intent=IntentType.INCENTIVE_RECOMMENDATION,
            confidence=0.78,
            is_in_scope=True,
            needs_user_profile=not is_profile_complete(user_profile),
            target_service=TargetService.MATCHING,
            extracted_profile=None,
            missing_fields=get_missing_profile_fields(user_profile),
            reason="Mesaj şirket profili ve destek ihtiyacı içeriyor.",
        )

    # 8. Belge, şart, başvuru gibi doküman tabanlı sorular RAG'e gider.
    rag_confidence = keyword_score(normalized_message, RAG_QUESTION_KEYWORDS)
    if rag_confidence > 0:
        return IntentResult(
            intent=IntentType.RAG_QUESTION,
            confidence=rag_confidence,
            is_in_scope=True,
            needs_user_profile=False,
            target_service=TargetService.RAG,
            extracted_profile=None,
            missing_fields=[],
            reason="Kullanıcı belge, şart, başvuru veya program detayı soruyor.",
        )

    # 9. Teşvik/destek kelimesi var ama niyet net değilse UNKNOWN.
    if contains_any(normalized_message, IN_SCOPE_KEYWORDS):
        maybe_unknown = IntentResult(
            intent=IntentType.UNKNOWN,
            confidence=0.45,
            is_in_scope=True,
            needs_user_profile=False,
            target_service=TargetService.ORCHESTRATION,
            extracted_profile=None,
            missing_fields=[],
            reason="Mesaj proje kapsamında ama niyet net değil.",
        )

        return maybe_use_llm_fallback(
            maybe_unknown,
            message,
            user_profile,
            use_llm_fallback=use_llm_fallback,
            llm_fallback=llm_fallback,
        )

    # 10. Hiçbir şeye girmiyorsa kapsam dışı veya bilinmeyen.
    unknown_result = IntentResult(
        intent=IntentType.OUT_OF_SCOPE,
        confidence=0.60,
        is_in_scope=False,
        needs_user_profile=False,
        target_service=TargetService.ORCHESTRATION,
        extracted_profile=None,
        missing_fields=[],
        reason="Mesaj teşvik/destek alanıyla ilişkili görünmüyor.",
    )

    return maybe_use_llm_fallback(
        unknown_result,
        message,
        user_profile,
        use_llm_fallback=use_llm_fallback,
        llm_fallback=llm_fallback,
    )


def maybe_use_llm_fallback(
    current_result: IntentResult,
    message: str,
    user_profile: UserProfile | None,
    *,
    use_llm_fallback: bool,
    llm_fallback: Callable[[str, UserProfile | None], IntentResult] | None,
) -> IntentResult:
    """
    Hybrid intent için genişleme noktası.

    Şu an MVP'de use_llm_fallback=False kalabilir.
    İleride:
        - confidence düşükse
        - intent UNKNOWN ise
        - mesaj kararsızsa

    llm_fallback fonksiyonu çağrılabilir.
    """

    should_fallback = (
        use_llm_fallback
        and llm_fallback is not None
        and (
            current_result.intent == IntentType.UNKNOWN
            or current_result.confidence < 0.70
        )
    )

    if should_fallback:
        return llm_fallback(message, user_profile)

    return current_result


def get_missing_profile_fields(user_profile: UserProfile | None) -> list[str]:
    """
    Matching için eksik profil alanlarını döndürür.
    Orchestrator bu alanlara göre kullanıcıdan eksik bilgi isteyebilir.
    """

    if user_profile is None:
        return ["sector", "employee_count", "annual_revenue", "needs"]

    missing_fields: list[str] = []

    if not user_profile.sector:
        missing_fields.append("sector")

    if user_profile.employee_count is None:
        missing_fields.append("employee_count")

    if user_profile.annual_revenue is None:
        missing_fields.append("annual_revenue")

    if not user_profile.needs:
        missing_fields.append("needs")

    return missing_fields


"""
test cases for intent detection
"""
"""
tests = [
    "Merhaba",
    "Bana uygun teşvikleri bul",
    "KOSGEB desteği için hangi belgeler gerekiyor?",
    "Bu desteğe uygun muyum?",
    "Çalışan sayımız 20 oldu",
    "Bugün hava nasıl?",
    "Destek hakkında bilgi almak istiyorum",
]

for text in tests:
    result = detect_intent(text)
    print(text, "=>", result.intent, result.confidence, result.reason)

"""