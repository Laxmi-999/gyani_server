import os

# Storage Configuration
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Comprehensive MIME Types for Images
IMAGE_MIME_TYPES = [
    "image/jpeg",
    "image/pjpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/x-ms-bmp",
    "image/tiff",
    "image/heic",
    "image/heif",
]

# Supported Document & Spreadsheet Extensions
DOC_EXTENSIONS = [
    # PDF
    ".pdf",
    
    # Word Documents
    ".docx",
    ".doc",
    
    # Excel & Spreadsheets
    ".xlsx",  # Standard Modern Excel
    ".xls",   # Legacy Excel (97-2003)
    ".csv",   # Comma-Separated Values
    ".tsv",   # Tab-Separated Values
    
    # Text & Code/Data
    ".txt",
    ".md",
    ".json",
    ".log",
]