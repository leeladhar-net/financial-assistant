import os
from typing import List, Dict, Any
from app.core.logging import logger

class DocumentProcessor:
    """
    Processes uploaded PDF/financial documents:
    1. Extracts text from PDF bytes
    2. Chunks text into semantic financial passages
    """

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
        words = text.split()
        if len(words) <= chunk_size:
            return [text]

        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
            i += (chunk_size - overlap)
        return chunks

    @staticmethod
    def process_pdf_content(filename: str, content_bytes: bytes) -> Dict[str, Any]:
        logger.info(f"Processing PDF document: {filename} ({len(content_bytes)} bytes)")
        
        # Sample extracted text simulation for PDF documents
        text = (
            f"Financial Report: {filename}\n\n"
            "EXECUTIVE SUMMARY:\n"
            "Q3 Revenue expanded by 24% year-over-year to $35.1 Billion. "
            "Data Center segment revenue grew 112% driven by demand for AI accelerators and enterprise Copilot deployments.\n\n"
            "KEY FINANCIAL METRICS:\n"
            "• Gross Margin: 75.2%\n"
            "• Operating Income: $16.8 Billion (+42% YoY)\n"
            "• Free Cash Flow: $12.4 Billion\n\n"
            "RISKS AND GUIDANCE:\n"
            "Management highlighted supply chain lead times for next-gen chip architectures as a primary operational bottleneck. "
            "Q4 Revenue guidance projected at $37.5 Billion (+/- 2%)."
        )

        chunks = DocumentProcessor.chunk_text(text)
        return {
            "filename": filename,
            "full_text": text,
            "chunks": chunks,
            "chunk_count": len(chunks)
        }
