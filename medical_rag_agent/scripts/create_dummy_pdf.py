from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import os

def create_simplified_dummy_pdf(filepath):
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica", 12)
    
    # Position text directly, without complex text objects if that was an issue
    text_lines = [
        "This is a test PDF document for the Medical RAG Agent project.",
        "It contains some sample text to verify parsing functionality.",
        "Section: Introduction. Content: Basics of RAG."
    ]
    
    y_position = 7.5 * inch
    for line in text_lines:
        c.drawString(1 * inch, y_position, line)
        y_position -= 0.25 * inch # Move down for next line
        
    c.save()

if __name__ == "__main__":
    # Ensure the path is relative to the project root if script is called from project root
    # For calling from scripts/ directory:
    script_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    pdf_path = os.path.join(project_root, "data", "dummy_document.pdf")
    
    # Create data directory if it doesn't exist
    data_dir = os.path.dirname(pdf_path)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    create_simplified_dummy_pdf(pdf_path)
    print(f"Simplified dummy PDF created at {pdf_path}")
