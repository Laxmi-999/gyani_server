import logging
from PIL import Image
import pytesseract
import pdfplumber
from pdf2image import convert_from_path
import docx
import openpyxl

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
    """Extracts text paragraphs from Word documents (.docx)."""
    try:
        doc = docx.Document(docx_path)
        full_text = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
        return "\n".join(full_text)
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

def extract_text_from_txt(txt_path: str) -> str:
    """Extracts content from plain text, markdown, CSV, or JSON files."""
    try:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"[TXT Extraction Error]: {e}")
        return ""