from __future__ import annotations

from shared.enums import Language
from shared.models import UserProfile, MatchResult, SourceChunk

class PromptBuilder:
    @staticmethod
    def build_generation_system_prompt(language: Language) -> str:
        """/rag/generate için sistem promptu."""
        if language == Language.EN:
            return (
                "You are an expert incentive and grant advisor. Your task is to analyze the matching support "
                "programs against the user's business profile and generate structured, detailed recommendations. "
                "Make sure your recommendations are precise, professional, and highlight the core benefits. "
                "You must strictly output your response in the requested JSON structure."
            )
        # Varsayılan TR
        return (
            "Sen devlet teşvikleri, hibeler ve destek programları konusunda uzman bir danışmansın. "
            "Görevin, eşleşen destek programlarını kullanıcının şirket profili ile karşılaştırarak "
            "detaylı, profesyonel ve doğrulanabilir açıklamalar (Recommendation) üretmektir.\n\n"
            "Önemli Kurallar:\n"
            "1. 'why_matched' alanında bu programın işletmeye neden uygun olduğunu teknik kriterlerle açıkla.\n"
            "2. 'eligibility_notes' alanında kritik başvuru şartlarını ve işletmenin durumunu vurgula.\n"
            "3. 'application_steps' alanında başvuru sürecinin aşamalarını net bir şekilde listele.\n"
            "4. 'required_documents' alanında bu başvuru için kesinlikle talep edilecek belgeleri belirt.\n"
            "5. Dil olarak tamamen Türkçe kullan.\n"
            "6. Yanıtını kesinlikle sadece sizden istenen JSON formatında dönmelisin."
        )

    @staticmethod
    def build_generation_user_prompt(
        user_profile: UserProfile,
        matches: list[MatchResult],
        contexts: list[SourceChunk]
    ) -> str:
        """/rag/generate için kullanıcı profili ve belgeleri birleştiren prompt."""
        
        # Kullanıcı Profil Bilgisi
        profile_str = (
            f"- Sektör: {user_profile.sector}\n"
            f"- Çalışan Sayısı: {user_profile.employee_count}\n"
            f"- Yıllık Ciro: {user_profile.annual_revenue} TL\n"
            f"- İhtiyaç Alanları: {', '.join(user_profile.needs)}\n"
            f"- Şehir: {user_profile.city or 'Belirtilmedi'}\n"
            f"- Şirket Tipi: {user_profile.company_type or 'Belirtilmedi'}\n"
            f"- Ek Açıklama: {user_profile.description or 'Yok'}\n"
        )

        # Eşleşen Programlar
        matches_str = ""
        for m in matches:
            matches_str += (
                f"ID: {m.program_id} | Adı: {m.program_name} | Kurum: {m.institution} | Skor: {m.score}\n"
            )

        # Bilgi Tabanından Gelen Detaylar (Qdrant chunks)
        context_str = ""
        for idx, ctx in enumerate(contexts):
            context_str += (
                f"[{idx+1}] Program ID: {ctx.program_id} | Kaynak: {ctx.source_file or 'Belge'}\n"
                f"Metin: {ctx.text}\n"
                "-------------------\n"
            )

        return (
            f"KULLANICI PROFİLİ:\n{profile_str}\n"
            f"EŞLEŞEN DESTEKLER:\n{matches_str}\n"
            f"PROGRAM DETAYLARI VE ŞARTLARI (KILAVUZLAR):\n{context_str}\n\n"
            "Analizini yap ve her eşleşen program için 'Recommendation' şemasına tam uygun JSON çıktısı üret."
        )

    @staticmethod
    def build_answer_system_prompt(language: Language) -> str:
        """Chat soruları (/rag/answer) için sistem promptu."""
        if language == Language.EN:
            return (
                "You are a helpful assistant for government supports. Answer the user's question accurately "
                "using ONLY the provided context. If the answer cannot be found in the context, politely state that."
            )
        return (
            "Sen devlet destekleri ve teşvikleri konusunda uzman bir asistansın. "
            "Kullanıcının sorusunu SADECE sana sağlanan döküman parçalarına (bağlama) sadık kalarak cevapla.\n\n"
            "Kurallar:\n"
            "1. Dökümanlarda yazmayan bilgileri uydurma (halüsinasyon üretme).\n"
            "2. Eğer dökümanlarda sorunun cevabı yoksa, 'Bu konuda belgelerimde yeterli bilgi bulunmuyor, "
            "ancak ilgili kurumun resmi sitesini kontrol edebilirsiniz.' şeklinde kibar bir cevap ver.\n"
            "3. Yanıtında hangi programlardan bahsettiğini net belirt."
        )

    @staticmethod
    def build_answer_user_prompt(
        user_message: str,
        contexts: list[SourceChunk],
        user_profile: UserProfile | None = None
    ) -> str:
        """Chat soruları için kullanıcı promptu."""
        context_str = ""
        for idx, ctx in enumerate(contexts):
            context_str += f"[{idx+1}] ({ctx.program_name or 'Genel'}): {ctx.text}\n---\n"

        profile_str = "Belirtilmedi"
        if user_profile:
            profile_str = f"Sektör: {user_profile.sector}, Çalışan: {user_profile.employee_count}, Ciro: {user_profile.annual_revenue}"

        return (
            f"Kullanıcı Şirket Profili: {profile_str}\n\n"
            f"Kılavuzlardan İlgili Bölümler:\n{context_str}\n"
            f"Kullanıcı Sorusu: {user_message}\n\n"
            "Cevap:"
        )