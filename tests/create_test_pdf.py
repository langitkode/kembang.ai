"""Create a simple test PDF for ingestion testing."""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import os

def create_test_pdf(output_path: str):
    """Create a simple test PDF with Indonesian text."""
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "Profil Perusahaan Test")
    
    # Content
    c.setFont("Helvetica", 12)
    y = height - 120
    
    content = [
        "Tentang Perusahaan:",
        "",
        "Kami adalah perusahaan teknologi yang bergerak di bidang AI dan machine learning.",
        "Fokus utama kami adalah membantu UMKM mengadopsi teknologi chatbot otomatis.",
        "",
        "Produk Unggulan:",
        "",
        "1. Chatbot WhatsApp - Auto-reply untuk customer service",
        "2. Knowledge Base - RAG pipeline untuk jawaban akurat",
        "3. Analytics Dashboard - Monitoring penggunaan dan biaya",
        "",
        "Kontak:",
        "",
        "Email: info@testcompany.com",
        "Website: www.testcompany.com",
        "Telepon: +62 812-3456-7890",
    ]
    
    for line in content:
        c.drawString(72, y, line)
        y -= 20
    
    c.save()
    print(f"Test PDF created: {output_path}")
    return output_path


if __name__ == "__main__":
    create_test_pdf("uploads/test_profile.pdf")
