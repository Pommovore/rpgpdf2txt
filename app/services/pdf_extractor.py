import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
from loguru import logger
import os

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts text using PyMuPDF. If the text is too short (maybe it's a scan),
    falls back to OCR using pdf2image and pytesseract.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")
        
    text = ""
    try:
        # Try PyMuPDF first
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
        
        # If we got meaningful text, return it
        if len(text.strip()) > 100:
            logger.info("Successfully extracted text using PyMuPDF.")
            return text.strip()
            
        logger.info("Extracted text is too short, assuming scanned document. Falling back to OCR.")
    except Exception as e:
        logger.warning(f"PyMuPDF failed, falling back to OCR: {e}")
        
    # Fallback to OCR
    try:
        images = convert_from_path(pdf_path)
        ocr_text = ""
        for i, img in enumerate(images):
            # Using French language if available, fallback to eng
            # Note: tesseract-ocr-fra needs to be installed on the system
            # If 'fra' fails due to missing language pack, it will default to English or fail.
            try:
                page_text = pytesseract.image_to_string(img, lang="fra")
            except:
                page_text = pytesseract.image_to_string(img) # fallback default
                
            ocr_text += page_text + "\n"
            
        logger.info("Successfully extracted text using OCR.")
        return ocr_text.strip()
    except Exception as e:
        logger.error(f"OCR Extraction failed: {e}")
        # Return whatever we got from PyMuPDF, even if short/empty
        return text.strip()
