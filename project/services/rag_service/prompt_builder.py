class PromptBuilder:
    @staticmethod
    def build_chat_prompt(query: str, context: str) -> str:
        """Sohbet asistanı için sistem ve bağlam yönergelerini birleştirir."""
        return (
            "Sen KOBİ'ler ve firmalar için uzman bir hibe ve teşvik danışmanısın.\n"
            "Aşağıdaki resmi kurum belgelerini (bağlamı) kullanarak kullanıcının sorusunu yanıtla.\n"
            "Eğer sorunun cevabı bu belgelerde kesin olarak geçmiyorsa, 'Bu bilgiye şu anki belgelerden ulaşamıyorum.' de ve asla uydurma.\n\n"
            f"--- KURUM BELGELERİ (BAĞLAM) ---\n{context}\n---------------------\n"
            f"Kullanıcının Sorusu: {query}\n"
            "Cevabınız: "
        )

    @staticmethod
    def build_generation_prompt(program_name: str) -> str:
        """Rapor üretimi için yapılandırılmış JSON şablonu promptunu oluşturur."""
        return f"""
        Sen uzman bir hibe danışmanısın. Sistemdeki belgelerden "{program_name}" isimli programın detaylarını bul.
        Senden bu bilgileri analiz edip AŞAĞIDAKİ JSON FORMATINDA KESİN BİR ŞEKİLDE döndürmeni istiyorum.
        
        Lütfen sadece JSON çıktısı ver, markdown (```json) kullanma, fazladan metin yazma:
        {{
            "program_name": "{program_name}",
            "amaci": "Programın temel amacı (1-2 cümle)",
            "kimler_basvurabilir": "Kimlerin başvurabileceği şartları (1-2 cümle)",
            "butce_limiti": "Maksimum bütçe ve/veya destek oranı",
            "adimlar": ["başvuru adımı 1", "başvuru adımı 2", "başvuru adımı 3"],
            "belgeler": ["istenilen belge 1", "istenilen belge 2"],
            "tahmini_sure": "Değerlendirme süresi veya projenin süresi"
        }}
        """