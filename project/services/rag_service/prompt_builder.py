from shared.models import MatchResult, SourceChunk, UserProfile


def format_user_profile(user_profile: UserProfile | None) -> str:
    if user_profile is None:
        return "Kullanıcı profili verilmedi."

    return f"""
Sektör: {user_profile.sector}
Çalışan sayısı: {user_profile.employee_count}
Yıllık ciro: {user_profile.annual_revenue}
Şehir: {user_profile.city or "Belirtilmedi"}
Şirket tipi: {user_profile.company_type or "Belirtilmedi"}
İhtiyaçlar: {", ".join(user_profile.needs)}
Açıklama: {user_profile.description or "Belirtilmedi"}
""".strip()


def format_sources(chunks: list[SourceChunk]) -> str:
    if not chunks:
        return "Kaynak bulunamadı."

    text = ""

    for index, chunk in enumerate(chunks, start=1):
        text += f"""
[KAYNAK {index}]
Program: {chunk.program_name}
Program ID: {chunk.program_id}
Metin:
{chunk.text}
""".strip()
        text += "\n\n"

    return text


def build_generate_prompt(
    user_profile: UserProfile,
    matches: list[MatchResult],
    chunks: list[SourceChunk],
) -> str:
    match_text = "\n".join(
        [
            f"- {m.program_name} | Kurum: {m.institution} | Skor: {m.score} | Nedenler: {', '.join(m.match_reasons)} | Eksikler: {', '.join(m.missing_criteria)}"
            for m in matches
        ]
    )

    return f"""
Kullanıcı profili:
{format_user_profile(user_profile)}

Matching sonuçları:
{match_text}

Kaynak belge parçaları:
{format_sources(chunks)}

Görev:
Bu kullanıcı için teşvik/destek önerilerini açıkla.

Cevap formatı:
- Kısa genel özet
- Her program için:
  - Program ne işe yarar?
  - Kullanıcıya neden uygun olabilir?
  - Dikkat edilmesi gereken uygunluk notları
  - Gerekli belgeler
  - Başvuru adımları
- Belgeye dayanmayan bilgi üretme.
""".strip()


def build_answer_prompt(
    user_message: str,
    user_profile: UserProfile | None,
    chunks: list[SourceChunk],
) -> str:
    return f"""
Kullanıcı sorusu:
{user_message}

Kullanıcı profili:
{format_user_profile(user_profile)}

Kaynak belge parçaları:
{format_sources(chunks)}

Görev:
Kullanıcının sorusunu sadece kaynaklara dayanarak cevapla.
Eğer kaynaklarda cevap yoksa açıkça "Bu bilgi belgelerde bulunamadı" de.
""".strip()