import os
import json
from dotenv import load_dotenv
import qdrant_client
from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding

# Shared katmanından resmi veri modelimizi çağırıyoruz (API Contract Uyumu)
from shared.models import ProgramDocument

load_dotenv()

# Embedding modeli ayarı (RAG ile ortak)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "output.json")

def run_ingestion():
    print("🚀 API Contract Uyumlu Ingestion Pipeline Başlatılıyor...")
    
    if not os.path.exists(JSON_PATH):
        print(f"❌ HATA: {JSON_PATH} bulunamadı! Lütfen data/output.json dosyasını buraya koyun.")
        return
        
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        ham_veriler = json.load(f)
        
    documents = []
    
    for d in ham_veriler:
        program_id = d.get("program_id", "id_belirtilmemis")
        program_name = d.get("program_name", "Bilinmeyen Program")
        institution = d.get("institution", "KOSGEB")
        application_url = d.get("url", "https://www.kosgeb.gov.tr")
        
        # Sections içindeki başlıkları ve içerikleri ayıklayalım
        sections = d.get("sections", [])
        
        amaci_text = ""
        sartlar_text = ""
        unsurlar_text = ""
        ekler_text = ""
        
        for sec in sections:
            title = sec.get("title", "").strip().lower()
            content = sec.get("content", "").strip()
            
            if "amaç" in title or "amacı" in title:
                amaci_text = content
            elif "şart" in title or "koşul" in title:
                sartlar_text = content
            elif "unsur" in title or "bütçe" in title:
                unsurlar_text = content
            elif "form" in title or "ekler" in title:
                ekler_text = content

        # AKILLI SEKTÖR VE İHTİYAÇ ETİKETLEME (Kategori tespiti)
        sectors = []
        tarama_metni = f"{program_name} {amaci_text} {sartlar_text}".lower()
        if any(k in tarama_metni for k in ["imalat", "sanayi", "üretim"]):
            sectors.append("İmalat")
        if any(k in tarama_metni for k in ["yazılım", "teknoloji", "bilişim", "bilgisayar", "ar-ge"]):
            sectors.append("Teknoloji")
        if any(k in tarama_metni for k in ["tarım", "hayvancılık", "gıda", "çiftçi"]):
            sectors.append("Tarım")
        if any(k in tarama_metni for k in ["hizmet", "ticaret", "eğitim", "danışmanlık"]):
            sectors.append("Hizmet")
            
        if not sectors:
            sectors = ["İmalat", "Teknoloji", "Tarım", "Hizmet"]

        needs = []
        tarama_metni_ihtiyac = f"{program_name} {amaci_text} {unsurlar_text}".lower()
        if any(k in tarama_metni_ihtiyac for k in ["personel", "istihdam", "maaş", "çalışan"]):
            needs.append("İstihdam")
        if any(k in tarama_metni_ihtiyac for k in ["ar-ge", "arge", "inovasyon", "tasarım"]):
            needs.append("Ar-Ge")
        if any(k in tarama_metni_ihtiyac for k in ["makine", "teçhizat", "yatırım", "yazılım", "kuruluş"]):
            needs.append("Yatırım")
        if any(k in tarama_metni_ihtiyac for k in ["ihracat", "pazarlama", "yurt dışı"]):
            needs.append("İhracat")
            
        if not needs:
            needs = ["Ar-Ge", "İstihdam", "Yatırım", "İhracat"]

        # --- VERİ DOĞRULAMA (Pydantic Validation) ---
        # Kazınan veriyi Qdrant'a yüklemeden önce API Contract şemasına göre denetliyoruz
        try:
            validated_doc = ProgramDocument(
                program_id=program_id,
                program_name=program_name,
                institution=institution,
                description=amaci_text if len(amaci_text) >= 10 else f"{program_name} resmi analiz dökümanıdır.",
                application_url=application_url,
                sectors=sectors,
                needs=needs,
                conditions=sartlar_text.split("\n") if sartlar_text else [],
                required_documents=ekler_text.split(",") if ekler_text else []
            )
        except Exception as ve:
            # Eğer veri sözleşmeye uymuyorsa hata logu basar ve bu hibe programını veritabanına eklemeden geçer (atlar)
            print(f"⚠️ UYARI: '{program_name}' verisi API Sözleşmesine uymadığı için atlandı! Hata: {ve}")
            continue
        # ---------------------------------------------

        # Vektör indeksleme için birleşik döküman metnini oluşturma
        document_text = f"""
        Program Adı: {validated_doc.program_name}
        Kurum: {validated_doc.institution}
        Amacı: {validated_doc.description}
        Başvuru Şartları: {sartlar_text}
        Destek Unsurları: {unsurlar_text}
        Belgeler & Formlar: {ekler_text}
        """

        # API Contract modelinden (validated_doc) doğrulanmış temiz üst bilgileri (metadata) alıyoruz
        metadata = {
            "program_id": validated_doc.program_id,
            "program_name": validated_doc.program_name,
            "institution": validated_doc.institution,
            "application_url": str(validated_doc.application_url),
            "sectors": validated_doc.sectors,
            "needs": validated_doc.needs
        }
        
        doc = Document(text=document_text, metadata=metadata, doc_id=validated_doc.program_id)
        documents.append(doc)
        
    print(f"📦 {len(documents)} adet döküman başarıyla doğrulandı ve hazırlandı. Qdrant'a yükleniyor...")
    
    try:
        client = qdrant_client.QdrantClient(url=QDRANT_URL)
        
        if client.collection_exists(collection_name="tesvikler_v2"):
            print("🗑️ Eski ve hatalı şemalı 'tesvikler_v2' tablosu otomatik siliniyor...")
            client.delete_collection(collection_name="tesvikler_v2")
        
        vector_store = QdrantVectorStore(
            client=client, 
            collection_name="tesvikler_v2",
            vector_name="text-dense"
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        VectorStoreIndex.from_documents(
            documents, 
            storage_context=storage_context
        )
        print("✅ BAŞARILI: Tüm dökümanlar API Sözleşmesine uygun olarak Qdrant'a kaydedildi!")
        
    except Exception as e:
        print(f"❌ HATA: Yükleme başarısız: {e}")

if __name__ == "__main__":
    run_ingestion()