import logging
import os
import shutil
from typing import Optional
from PIL import Image
import pymupdf
import pytesseract

logger = logging.getLogger(__name__)

class OCRService:
    """
    Provides Optical Character Recognition (OCR) using Tesseract.
    Converts PDF page pixmaps to PIL Images and extracts text from scanned or image-based pages.
    """

    def __init__(self, tesseract_cmd: Optional[str] = None):
        self.tesseract_cmd = tesseract_cmd or self._find_tesseract_binary()
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            logger.info(f"Tesseract OCR initialized with binary: {self.tesseract_cmd}")
        else:
            logger.warning("Tesseract binary not found. OCR capabilities will be disabled.")

    def _find_tesseract_binary(self) -> Optional[str]:
        # Check environment variable first
        env_cmd = os.getenv("TESSERACT_CMD")
        if env_cmd and os.path.isfile(env_cmd) and os.access(env_cmd, os.X_OK):
            return env_cmd

        # Check standard PATH
        which_cmd = shutil.which("tesseract")
        if which_cmd:
            return which_cmd

        # Check known OS binary locations
        common_locations = [
            "/opt/homebrew/bin/tesseract",       # macOS Apple Silicon Homebrew
            "/usr/local/bin/tesseract",          # macOS Intel / Linux local
            "/usr/bin/tesseract",                # Debian / Ubuntu
            "/bin/tesseract",
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",  # Windows standard
        ]
        for loc in common_locations:
            if os.path.isfile(loc) and os.access(loc, os.X_OK):
                return loc

        return None

    def is_available(self) -> bool:
        """Checks if Tesseract OCR is installed and accessible."""
        if not self.tesseract_cmd:
            return False
        try:
            version = pytesseract.get_tesseract_version()
            return version is not None
        except Exception as e:
            logger.warning(f"Tesseract check failed: {e}")
            return False

    def ocr_page(self, page: pymupdf.Page, dpi: int = 200, lang: str = "eng") -> str:
        """
        Renders a PyMuPDF Page to an image and performs OCR text extraction.
        
        Args:
            page: PyMuPDF Page object
            dpi: Resolution for rendering (200 DPI is optimal for balance of speed & accuracy)
            lang: Tesseract language code ('eng' by default)
            
        Returns:
            Extracted text string from OCR
        """
        if not self.is_available():
            logger.warning("OCR requested but Tesseract binary is not available.")
            return ""

        try:
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            text = pytesseract.image_to_string(img, lang=lang, config="--psm 3")
            return text.strip()
        except Exception as e:
            logger.error(f"OCR execution failed on page {page.number + 1}: {e}")
            return ""

    def ocr_pil_image(self, img: Image.Image, lang: str = "eng") -> str:
        """Performs OCR on a PIL Image object."""
        if not self.is_available():
            return ""
        try:
            return pytesseract.image_to_string(img, lang=lang, config="--psm 3").strip()
        except Exception as e:
            logger.error(f"OCR failed on PIL Image: {e}")
            return ""

ocr_service = OCRService()
