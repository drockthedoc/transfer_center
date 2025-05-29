import PyPDF2
import os
import textwrap # Ensure textwrap is imported

def parse_pdf(filepath):
    try:
        with open(filepath, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            if len(reader.pages) > 0:
                first_page = reader.pages[0]
                text = first_page.extract_text()
                return text
            else:
                return "Error: PDF is empty."
    except Exception as e:
        return f"Error parsing PDF: {e}"

if __name__ == "__main__":
    # Adjust path to be relative to the script's location in scripts/
    # For robust path handling if script is called from scripts/
    script_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    pdf_path = os.path.join(project_root, "data", "dummy_document.pdf")

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
    else:
        extracted_text = parse_pdf(pdf_path)
        print("Extracted Text from PDF:")
        print(textwrap.fill(extracted_text, width=100) if extracted_text else "No text extracted or error occurred.")

# Note: PyPDF2 can sometimes have issues with text extraction from complex PDFs or those created by certain tools.
# The dummy PDF created by reportlab should be simple enough.
