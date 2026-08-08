import pytest
from app.services.user_service import UserService
from app.retrieval.document_processor import DocumentProcessor
from app.retrieval.vector_store import VectorStore

def test_document_processor_chunking():
    sample_text = "Word " * 1000
    chunks = DocumentProcessor.chunk_text(sample_text, chunk_size=400, overlap=50)
    assert len(chunks) > 1

def test_vector_store_indexing_and_rag_query(db_session):
    user = UserService.get_or_create_user(db_session, telegram_user_id=7701)
    
    # Process sample PDF content
    filename = "Nvidia_Q3_Earnings_Report.pdf"
    content_bytes = b"Sample PDF Bytes"
    processed = DocumentProcessor.process_pdf_content(filename, content_bytes)
    
    # Index document in Vector Store
    doc = VectorStore.index_document(db_session, user.id, filename, processed["chunks"])
    assert doc.id is not None
    assert doc.filename == filename

    # Perform RAG Query
    query = "What is Nvidia Q3 Revenue and Data Center growth?"
    rag_res = VectorStore.query_document_rag(db_session, user.id, query)
    
    assert rag_res is not None
    assert rag_res.document_name == filename
    assert "Q3 Revenue" in rag_res.answer
    assert len(rag_res.sources) > 0
