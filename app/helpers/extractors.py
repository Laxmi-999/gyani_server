import os
import logging
from PIL import Image
import pytesseract
import pdfplumber
from pdf2image import convert_from_path
import docx
import openpyxl
from bs4 import BeautifulSoup
import io
from docx.opc.constants import RELATIONSHIP_TYPE as RT


logger = logging.getLogger(__name__)


def extract_text_from_image(image_path: str) -> str:
    """Extracts text from image formats (.jpg, .png, .webp, etc.) using PyTesseract."""
    try:
        image = Image.open(image_path)
        raw_text = pytesseract.image_to_string(image)
        return raw_text.strip() if raw_text else ""
    except Exception as e:
        logger.error(f"[Image OCR Error]: {e}")
        return ""

    
def extract_text_from_html(html_path: str) -> str:
    """Strips HTML markup and extracts plain text content."""
    try:
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            # Strip script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        logger.error(f"[HTML Extraction Error]: {e}")
        return ""


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts text from PDFs. Falls back to OCR via pdf2image if no native digital text is found."""
    extracted_text = ""

    # Try native digital text extraction
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
    except Exception as e:
        logger.warning(f"[PDF Extraction] pdfplumber failed: {e}")

    # Fallback: Run OCR on scanned PDF pages
    if not extracted_text.strip():
        logger.info(f"[PDF Extraction] No native text in {pdf_path}. Running OCR via pdf2image...")
        try:
            images = convert_from_path(pdf_path)
            for img in images:
                page_ocr = pytesseract.image_to_string(img)
                extracted_text += page_ocr + "\n"
        except Exception as e:
            logger.error(f"[PDF Extraction] pdf2image OCR failed: {e}")

    return extracted_text.strip()




def extract_text_from_docx(docx_path: str) -> str:
    """Extracts text from Word documents (.docx): regular paragraphs, tables,
    and OCR'd text from any embedded images (e.g. pasted screenshots)."""
    try:
        doc = docx.Document(docx_path)
        parts = []

        # 1. Regular paragraph text
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                parts.append(paragraph.text.strip())

        # 2. Table content
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    parts.append(" | ".join(row_cells))

        # 3. Embedded images (e.g. pasted screenshots) — run OCR on each
        image_rels = [
            rel for rel in doc.part.rels.values()
            if rel.reltype == RT.IMAGE
        ]
        for i, rel in enumerate(image_rels):
            try:
                image_bytes = rel.target_part.blob
                image = Image.open(io.BytesIO(image_bytes))
                ocr_text = pytesseract.image_to_string(image).strip()
                if ocr_text:
                    parts.append(f"--- Embedded image {i + 1} (OCR) ---\n{ocr_text}")
            except Exception as img_err:
                logger.warning(f"[DOCX Extraction] Failed to OCR embedded image {i + 1}: {img_err}")

        return "\n".join(parts)
    except Exception as e:
        logger.error(f"[DOCX Extraction Error]: {e}")
        return ""

def extract_text_from_excel(excel_path: str) -> str:
    """Extracts text content from all sheets in an Excel (.xlsx, .xls) workbook."""
    try:
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        extracted_text = []

        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            extracted_text.append(f"--- Sheet: {sheet_name} ---")
            
            for row in sheet.iter_rows(values_only=True):
                # Filter out completely empty rows
                row_values = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
                if row_values:
                    extracted_text.append(" | ".join(row_values))

        return "\n".join(extracted_text)
    except Exception as e:
        logger.error(f"[Excel Extraction Error]: {e}")
        return ""


def extract_text_from_file(file_path: str, content_type: str = "") -> str:
    """
    Main dispatcher: Routes file extraction based on extension or MIME type.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"]:
        return extract_text_from_image(file_path)
    elif ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        return extract_text_from_docx(file_path)
    elif ext in [".xlsx", ".xls"]:
        return extract_text_from_excel(file_path)
    elif ext in [".html", ".htm"]:
        return extract_text_from_html(file_path)
    elif ext in [".txt", ".md", ".csv", ".json", ".log"]:
        return extract_text_from_txt(file_path)
    else:
        logger.warning(f"Unsupported file extension for extraction: {ext}")
        return ""

    
def extract_text_from_txt(txt_path: str) -> str:
    """Extracts content from plain text, markdown, CSV, or JSON files."""
    try:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"[TXT Extraction Error]: {e}")
        return ""