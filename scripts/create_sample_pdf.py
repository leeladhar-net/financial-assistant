import os

def create_simple_pdf(output_path: str):
    """
    Generates a valid, clean sample financial PDF report for testing document upload in Telegram.
    """
    content = (
        "%PDF-1.4\n"
        "1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        "2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        "3 0 obj <</Type /Page /Parent 2 0 R /Resources <</Font <</F1 4 0 R>>>> /MediaBox [0 0 612 792] /Contents 5 0 R>> endobj\n"
        "4 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n"
        "5 0 obj <</Length 600>> stream\n"
        "BT\n"
        "/F1 18 Tf\n"
        "50 740 Td (NVIDIA CORPORATION - Q3 FINANCIAL REPORT) Tj\n"
        "0 -30 Td\n"
        "/F1 12 Tf\n"
        "(1. EXECUTIVE SUMMARY) Tj\n"
        "0 -20 Td\n"
        "(Q3 Revenue expanded by 24% year-over-year to $35.1 Billion.) Tj\n"
        "0 -15 Td\n"
        "(Data Center segment revenue grew 112% YoY driven by AI accelerator demand.) Tj\n"
        "0 -30 Td\n"
        "(2. FINANCIAL METRICS) Tj\n"
        "0 -20 Td\n"
        "(- Gross Margin: 75.2%) Tj\n"
        "0 -15 Td\n"
        "(- Operating Income: $16.8 Billion (+42% YoY)) Tj\n"
        "0 -15 Td\n"
        "(- Free Cash Flow: $12.4 Billion) Tj\n"
        "0 -30 Td\n"
        "(3. RISKS & OUTLOOK) Tj\n"
        "0 -20 Td\n"
        "(- Supply chain lead times for next-gen chip architectures remain a bottleneck.) Tj\n"
        "0 -15 Td\n"
        "(- Q4 Revenue guidance projected at $37.5 Billion.) Tj\n"
        "ET\n"
        "endstream\n"
        "endobj\n"
        "xref\n"
        "0 6\n"
        "0000000000 65535 f \n"
        "0000000009 00000 n \n"
        "0000000062 00000 n \n"
        "0000000117 00000 n \n"
        "0000000234 00000 n \n"
        "0000000305 00000 n \n"
        "trailer <</Size 6 /Root 1 0 R>>\n"
        "startxref\n"
        "960\n"
        "%%EOF\n"
    )
    with open(output_path, "wb") as f:
        f.write(content.encode("latin-1"))
    print(f"Sample PDF created at: {output_path}")

if __name__ == "__main__":
    pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Nvidia_Q3_Earnings_Report.pdf"))
    create_simple_pdf(pdf_path)
