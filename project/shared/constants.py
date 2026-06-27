"""
Projede tekrar tekrar kullanılan sabit değerleri merkezi tutmak için kullanılır.

Endpoint pathleri, servis isimleri, varsayılan limitler ve ortak mesajlar
her serviste aynı yazılsın diye burada tutulur.
"""

# Servis adları
ORCHESTRATION_SERVICE_NAME = "orchestration_service"
MATCHING_SERVICE_NAME = "matching_service"
RAG_SERVICE_NAME = "rag_service"
INGESTION_SERVICE_NAME = "ingestion_service"

# Endpoint pathleri
HEALTH_PATH = "/health"

RECOMMEND_PATH = "/recommend"
CHAT_PATH = "/chat"

MATCH_PATH = "/match"

RAG_GENERATE_PATH = "/rag/generate"
RAG_ANSWER_PATH = "/rag/answer"

INGEST_PATH = "/ingest"

# Varsayılan değerler
DEFAULT_LANGUAGE = "tr"
DEFAULT_TOP_K = 5
MAX_TOP_K = 20

DEFAULT_TOP_K_CHUNKS = 5
MAX_TOP_K_CHUNKS = 20

# RAG güvenlik mesajı
DEFAULT_DISCLAIMER = (
    "Bu öneriler bilgilendirme amaçlıdır; resmi uygunluk veya başvuru garantisi vermez."
)

# Genel cevaplar
GREETING_MESSAGE = (
    "Merhaba, size işletmenize uygun teşvik ve destekleri bulmada yardımcı olabilirim. "
    "Şirketinizin sektörü, çalışan sayısı, şehir ve destek ihtiyacını paylaşırsanız başlayabiliriz."
)

OUT_OF_SCOPE_MESSAGE = (
    "Bu sistem özellikle işletmelere uygun teşvik ve destekleri bulmak için tasarlandı. "
    "Şirketinizle ilgili teşvik, destek, başvuru şartı veya uygunluk sorularında yardımcı olabilirim."
)

GENERAL_INFO_MESSAGE = (
    "Bu sistem, işletmenizin bilgilerine göre uygun teşvik ve destekleri bulmanıza "
    "yardımcı olur. Formdan şirket bilgilerinizi girerek öneri alabilir veya chat "
    "üzerinden başvuru şartları, belgeler ve uygunluk hakkında soru sorabilirsiniz."
)

UNKNOWN_INTENT_MESSAGE = (
    "Tam olarak ne istediğinizi anlayamadım. İşletmenize uygun destekleri mi bulmamı istiyorsunuz, "
    "yoksa belirli bir destek hakkında bilgi mi almak istiyorsunuz?"
)

NO_MATCH_MESSAGE = (
    "Verdiğiniz bilgilere göre net bir destek eşleşmesi bulunamadı. "
    "Daha doğru sonuç için sektör, çalışan sayısı, şehir ve ihtiyaç alanınızı detaylandırabilirsiniz."
)

NO_RAG_CONTEXT_MESSAGE = (
    "Bu konuda bilgi tabanında yeterli kaynak bulamadım. "
    "Destek adını veya başvuru konusunu biraz daha net yazarak tekrar sorabilirsiniz."
)