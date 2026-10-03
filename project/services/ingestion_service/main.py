import os
import json
from uuid import uuid4
from qdrant_client import models
from shared.config import settings
from dotenv import load_dotenv
import qdrant_client
from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding

# Shared katmanından resmi veri modelimizi çağırıyoruz (API Contract Uyumu)
from shared.models import ProgramDocument

load_dotenv()



QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "output.json")

def run_ingestion():
    print("🚀 API Contract Uyumlu Ingestion Pipeline Başlatılıyor...")
    
    if not os.path.exists(JSON_PATH):
        print(f"❌ HATA: {JSON_PATH} bulunamadı! Lütfen data/output.json dosyasını buraya koyun.")
        raise FileNotFoundError(JSON_PATH)
        
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        ham_veriler = json.load(f)
        
    if not isinstance(ham_veriler, list) or not ham_veriler:
        raise ValueError("Kaynak veri boş veya geçersiz; mevcut indeks korunuyor.")

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
                source_url=application_url,
                last_updated=d.get("scraped_at"),
                sectors=sectors,
                needs=needs,
                conditions=sartlar_text.split("\n") if sartlar_text else [],
                required_documents=ekler_text.split(",") if ekler_text else []
            )
        except Exception as ve:
            # Kısmi veya geçersiz veriyle mevcut indeksi değiştirme.
            print(f"⚠️ UYARI: '{program_name}' verisi API Sözleşmesine uymuyor; işlem durduruldu! Hata: {ve}")
            raise ValueError(f"Geçersiz program: {program_id}; mevcut indeks korunuyor.") from ve
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
        metadata = validated_doc.model_dump(mode="json", exclude_none=True)
        # Başlık bazlı özetleme dışında kalan metin ve kaynak bağlantılarını da koru.
        document_text += "\n" + "\n\n".join(
            f"{sec.get('title', '')}\n{sec.get('content', '')}\n"
            + "\n".join(link.get('href', '') for link in sec.get('links', []))
            for sec in sections
        )

        doc = Document(
            text=document_text, metadata=metadata, doc_id=validated_doc.program_id,
            # Structured fields remain in Qdrant; full content is already in text.
            excluded_embed_metadata_keys=list(metadata),
            excluded_llm_metadata_keys=list(metadata),
        )
        documents.append(doc)
        
    print(f"📦 {len(documents)} adet döküman başarıyla doğrulandı ve hazırlandı. Qdrant'a yükleniyor...")
    
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    client = qdrant_client.QdrantClient(url=QDRANT_URL)
    try:
        publish_documents(client, documents, settings.QDRANT_COLLECTION_NAME)
    finally:
        client.close()


def publish_documents(client, documents, target):
    """Build in isolation, then atomically switch an alias. Never delete old data."""
    if not documents:
        raise ValueError("Boş indeks yayınlanamaz.")
    aliases = {item.alias_name: item.collection_name for item in client.get_aliases().aliases}
    if target not in aliases and client.collection_exists(target):
        raise ValueError(
            f"{target} fiziksel koleksiyon. Eski veriyi korumak için tüm servislerde "
            "QDRANT_COLLECTION_NAME=tesvikler_live kullanın ve ingestion'ı yeniden çalıştırın."
        )
    staging = f"{target}_build_{uuid4().hex}"
    nodes = Settings.node_parser.get_nodes_from_documents(documents)
    if not nodes:
        raise ValueError("İndekslenecek metin bulunamadı.")
    embeddings = Settings.embed_model.get_text_embedding_batch(
        [node.get_content(metadata_mode="embed") for node in nodes]
    )
    for node, embedding in zip(nodes, embeddings, strict=True):
        node.embedding = embedding
    # Explicit schema: adapter defaults can otherwise create unnamed vectors.
    client.create_collection(staging, vectors_config={
        settings.QDRANT_VECTOR_NAME: models.VectorParams(
            size=len(embeddings[0]), distance=models.Distance.COSINE
        )
    })
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=staging,
        dense_vector_name=settings.QDRANT_VECTOR_NAME,
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    # Any indexing exception leaves the currently published alias untouched.
    VectorStoreIndex(nodes, storage_context=storage_context)
    if client.count(staging, exact=True).count != len(nodes):
        raise ValueError("Yeni indeks eksik; mevcut hedef korunuyor.")
    operations = []
    if target in aliases:
        operations.append(models.DeleteAliasOperation(delete_alias=models.DeleteAlias(alias_name=target)))
    operations.append(models.CreateAliasOperation(
        create_alias=models.CreateAlias(collection_name=staging, alias_name=target)
    ))
    client.update_collection_aliases(change_aliases_operations=operations)
    # Old and failed builds remain available for inspection/rollback; no auto-delete.
    print(f"✅ Yeni indeks yayınlandı: {target} -> {staging}")
    return staging

if __name__ == "__main__":
    run_ingestion()