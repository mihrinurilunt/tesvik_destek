from typing import List, Optional
from shared.models import UserProfile, MatchResult, Recommendation


def build_recommendation_prompt(profile: UserProfile, match: MatchResult, context_text: str) -> str:
    """
    Eşleşen her bir teşvik için kişiselleştirilmiş 'Recommendation' nesnesini oluşturacak promptu yapılandırır.
    """
    profile_needs = ", ".join(profile.needs) if profile.needs else "Belirtilmemiş"
    match_reasons_str = ", ".join(match.match_reasons) if match.match_reasons else "Belirtilmemiş"
    missing_criteria_str = ", ".join(match.missing_criteria) if match.missing_criteria else "Belirtilmemiş"
    
    return f"""Sen devlet teşvikleri ve hibe programları alanında uzman bir analiz asistanısın.
Sana verilen kullanıcı profili ve eşleşen program bilgilerini, resmi döküman bağlamını da en ince ayrıntısına kadar göz önüne alarak değerlendirmeli ve son derece detaylı bir 'Recommendation' analizi çıkarmalısın.

Kullanıcı Şirket Profili:
- Sektör: {profile.sector}
- Çalışan Sayısı: {profile.employee_count}
- Yıllık Ciro: {profile.annual_revenue} TL
- İhtiyaçlar: {profile_needs}
- Şehir: {profile.city or "Belirtilmemiş"}
- Şirket Tipi: {profile.company_type or "Belirtilmemiş"}
- Açıklama: {profile.description or "Belirtilmemiş"}

Eşleşen Teşvik Detayı:
- Program Adı: {match.program_name}
- Kurum: {match.institution}
- Eşleşme Nedenleri: {match_reasons_str}
- Kritik Eksiklikler/Şartlar: {missing_criteria_str}

Resmi Belge Bağlamı (Veritabanından Gelen İlgili Parçalar):
{context_text or "Bu program hakkında doğrudan veritabanı belgesi bulunamadı."}

Senden sadece aşağıdaki JSON formatında yanıt üretmeni bekliyorum. Markdown etiketleri (```json vb.) kullanma, sadece saf JSON döndür.

Çıktı JSON Şeması:
{{
  "summary": "Kullanıcıya bu teşviğin tam olarak ne sunduğunu (bütçe limitleri, oranlar ve destek kalemleri dahil) ve şirketin ihtiyacına nasıl doğrudan çözüm olacağını açıklayan 3-4 cümlelik profesyonel ve rakamsal özet.",
  "why_matched": [
    "Kullanıcı profilinin ve hedeflerinin bu programla neden tam örtüştüğünü gösteren, dökümandaki kriterlerle desteklenmiş somut analiz maddeleri (en az 2 detaylı madde)."
  ],
  "eligibility_notes": [
    "Kullanıcının bu program kapsamında dikkat etmesi gereken kritik uygunluk şartları, başvuru engelleri, kısıtlamalar ve riskler (en az 2 detaylı madde)."
  ],
  "application_steps": [
    "Belgelere dayalı olarak, kullanıcının adım adım izlemesi gereken resmi başvuru ve onay süreci adımları."
  ],
  "required_documents": [
    "Başvuru esnasında ilgili kurum portalına yüklenmesi gereken zorunlu resmi belgeler ve formlar."
  ]
}}"""


def build_overall_answer_prompt(profile: UserProfile, recommendations: List[Recommendation]) -> str:
    """
    Kullanıcıya sunulan tüm önerileri değerlendiren genel bir karşılama ve özet yazısı promptunu oluşturur.
    """
    rec_list_str = "\n".join([f"- {r.institution} - {r.program_name}: {r.summary}" for r in recommendations])
    profile_needs = ", ".join(profile.needs) if profile.needs else "Belirtilmemiş"
    
    return f"""Kullanıcı için en uygun teşvikleri belirledik ve listeledik. Şimdi kullanıcıya hitaben son derece profesyonel, yol gösterici ve detay odaklı bir rehberlik giriş yazısı hazırlamalısın.

Kullanıcı Profili:
- Sektör: {profile.sector}
- Çalışan Sayısı: {profile.employee_count}
- İhtiyaçlar: {profile_needs}

Önerilen Destekler:
{rec_list_str}

Görevin:
Kullanıcıya hitaben Türkçe bir giriş yazısı oluştur. Bu desteklerin firmanın hedeflerine ve ihtiyaçlarına nasıl katkı sunacağını, bütçesel ve operasyonel faydalarını vurgulayarak açıkla. Yazının sonunda her bir teşviğin detaylı analiz raporunun aşağıda sunulduğunu ifade et."""


def build_answer_prompt(
    user_message: str, 
    context_text: str, 
    profile: Optional[UserProfile],
    focused_program_name: Optional[str] = None
) -> str:
    """
    Genel veya odaklanılmış soru-cevap akışı için sistem promptunu hazırlar.
    """
    profile_info = "Belirtilmemiş"
    if profile:
        profile_info = f"Sektör: {profile.sector}, Çalışan: {profile.employee_count}, Ciro: {profile.annual_revenue} TL"

    focus_instruction = ""
    if focused_program_name:
        focus_instruction = f"\n⚠️ ÖNEMLİ: Kullanıcı şu anda özellikle '{focused_program_name}' programı hakkında soru sormaktadır. Cevabını tamamen bu program çerçevesinde şekillendir ve dışına çıkmamaya özen göster."

    return f"""Sen resmi devlet destekleri, hibeler ve teşvik dökümanları üzerine çalışan son derece güvenilir, detaycı ve profesyonel bir asistanısın.
Sana iletilen döküman parçalarını (Bağlam) kullanarak kullanıcının sorusunu en doğru, eksiksiz ve anlaşılır biçimde cevaplamalısın.
{focus_instruction}

Kullanıcı Profili: {profile_info}
Kullanıcı Sorusu: {user_message}

Resmi Bağlam (Veritabanından Gelen Kayıtlar):
{context_text}

UYULMASI ZORUNLU KURALLAR:
1. Eğer sorunun cevabı "Resmi Bağlam" içerisinde bulunuyorsa, buradaki resmi verilere sıkı sıkıya sadık kalarak; destek bütçeleri, hibe oranları, başvuru süreleri ve şartları gibi tüm kritik rakamsal detayları içeren, maddeler halinde yapılandırılmış, son derece detaylı ve açıklayıcı bir yanıt hazırla. Yüzeysel veya tek cümlelik yanıtlardan kaçın.
2. EĞER sorunun cevabı dökümanlarda (Bağlam) YOKSA veya yetersiz kalıyorsa:
   - Kendi genel bilgi birikimini kullanarak kullanıcıya en yararlı, yapıcı ve profesyonel yanıtı sun.
   - Ancak yanıtının en sonuna şu uyarı şablonunu mutlaka ekle: "⚠️ Not: Bu bilgi veri tabanımızdaki dökümanlarda yer almamaktadır. Genel bilgi birikimim doğrultusunda hazırlanan bu yanıtın güncelliğini ilgili kurumun resmi sitesinden teyit etmeniz önerilir."
3. Yanıt dilini her zaman profesyonel, yapıcı ve Türkçe tut. Markdown elementlerini (başlıklar, kalın yazılar, listeler) kullanarak okunabilirliği maksimum düzeye çıkar."""