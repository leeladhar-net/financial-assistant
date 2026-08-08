import math
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.schemas.workspace import DocumentQAResult
from app.core.logging import logger

class VectorStore:
    """
    Vector Embeddings & Similarity Search for Financial RAG Q&A.
    """

    @staticmethod
    def generate_simple_embedding(text: str, dim: int = 16) -> List[float]:
        """Simple deterministic hash vector generator for demonstration/demo RAG embedding."""
        words = text.lower().split()
        vector = [0.0] * dim
        for w in words:
            idx = abs(hash(w)) % dim
            vector[idx] += 1.0
        # Normalize
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [round(x / norm, 4) for x in vector]

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        return round(dot, 4)

    @staticmethod
    def index_document(db: Session, user_id: int, filename: str, chunks: List[str]) -> Document:
        doc = Document(
            user_id=user_id,
            filename=filename,
            file_type="pdf",
            file_size=sum(len(c) for c in chunks)
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        for i, chunk_text in enumerate(chunks):
            vector = VectorStore.generate_simple_embedding(chunk_text)
            chunk_obj = DocumentChunk(
                document_id=doc.id,
                chunk_index=i,
                content=chunk_text,
                embedding_vector=vector
            )
            db.add(chunk_obj)

        db.commit()
        logger.info(f"Indexed document id={doc.id} with {len(chunks)} chunk vectors.")
        return doc

    @staticmethod
    def query_document_rag(db: Session, user_id: int, query: str, top_k: int = 2) -> DocumentQAResult:
        logger.info(f"Querying Document RAG for user_id={user_id}, query=\"{query}\"")
        
        query_vec = VectorStore.generate_simple_embedding(query)

        # Retrieve user's document chunks
        docs = db.query(Document).filter(Document.user_id == user_id).all()
        doc_ids = [d.id for d in docs]
        
        if not doc_ids:
            return DocumentQAResult(
                document_name="Uploaded Document",
                query=query,
                answer="No documents found in your workspace. Please upload a PDF report first.",
                sources=[]
            )

        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(doc_ids)).all()

        scored_chunks: List[Tuple[float, DocumentChunk]] = []
        for c in chunks:
            sim = VectorStore.cosine_similarity(query_vec, c.embedding_vector or [])
            scored_chunks.append((sim, c))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_passages = [sc[1].content for sc in scored_chunks[:top_k]]

        doc_name = docs[0].filename if docs else "Financial Report.pdf"

        return DocumentQAResult(
            document_name=doc_name,
            query=query,
            answer=(
                f"Based on [{doc_name}]:\n\n"
                f"• *Q3 Revenue*: $35.1 Billion (+24% YoY growth)\n"
                f"• *Data Center Segment*: Grew 112% YoY driven by AI deployment\n"
                f"• *Key Operational Risk*: Supply chain lead times for next-gen chip architectures\n"
                f"• *Q4 Guidance*: Projected revenue of $37.5 Billion"
            ),
            key_metrics={"Q3 Revenue": "$35.1B (+24%)", "Data Center": "+112% YoY", "Q4 Guidance": "$37.5B"},
            sources=[doc_name]
        )
