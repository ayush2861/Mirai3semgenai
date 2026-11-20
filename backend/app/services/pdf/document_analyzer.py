import logging
import statistics
from typing import List, Dict, Any, Tuple
import pymupdf

from app.schemas.universal_pdf import HeadingItem, DocumentAnalysis

logger = logging.getLogger(__name__)

class DocumentAnalyzer:
    """
    Analyzes PDF document geometry, typography, and page layout.
    Detects headings, multi-column reading order, and classifies document/page types.
    """

    def analyze_page_layout(self, page: pymupdf.Page, page_number: int) -> Dict[str, Any]:
        """
        Analyzes a single page layout: font statistics, headings, column count, and image presence.
        """
        text_dict = page.get_text("dict")
        page_width = page.rect.width
        page_height = page.rect.height

        font_sizes: List[float] = []
        headings: List[HeadingItem] = []
        images = page.get_images()
        has_images = len(images) > 0

        # Collect font statistics weighted by character count to determine baseline body font size
        font_char_counts = {}
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        size = round(span.get("size", 10.0), 1)
                        if text:
                            font_char_counts[size] = font_char_counts.get(size, 0) + len(text)

        if font_char_counts:
            # Baseline body font size is the font size that accounts for the most characters
            baseline_body_font = max(font_char_counts.items(), key=lambda item: item[1])[0]
        else:
            baseline_body_font = 10.0

        # Extract headings based on font size ratio to baseline body font
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    line_text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
                    if not line_text or len(line_text) > 200:
                        continue

                    # Examine largest span in line
                    max_span = max(line.get("spans", []), key=lambda s: s.get("size", 0.0), default={})
                    span_size = max_span.get("size", 10.0)
                    is_bold = bool(max_span.get("flags", 0) & 2) or ("bold" in max_span.get("font", "").lower())

                    # Level 1 heading: >= 1.5x body font or >= 20pt
                    if span_size >= max(baseline_body_font * 1.5, 20.0):
                        headings.append(HeadingItem(
                            level=1,
                            text=line_text,
                            page_number=page_number,
                            font_size=round(span_size, 1),
                            bbox=list(line.get("bbox", []))
                        ))
                    # Level 2 heading: >= 1.25x body font or >= 14pt
                    elif span_size >= max(baseline_body_font * 1.25, 14.0) or (is_bold and span_size >= baseline_body_font * 1.15):
                        headings.append(HeadingItem(
                            level=2,
                            text=line_text,
                            page_number=page_number,
                            font_size=round(span_size, 1),
                            bbox=list(line.get("bbox", []))
                        ))
                    # Level 3 heading: bold with body font
                    elif is_bold and span_size >= baseline_body_font and len(line_text) < 100 and not line_text.endswith("."):
                        headings.append(HeadingItem(
                            level=3,
                            text=line_text,
                            page_number=page_number,
                            font_size=round(span_size, 1),
                            bbox=list(line.get("bbox", []))
                        ))

        # Detect multi-column text layout using text blocks
        columns_detected, ordered_blocks = self.order_reading_blocks(page, page_width)

        return {
            "median_font_size": baseline_body_font,
            "headings": headings,
            "has_images": has_images,
            "image_count": len(images),
            "columns_detected": columns_detected,
            "ordered_blocks": ordered_blocks
        }

    def order_reading_blocks(self, page: pymupdf.Page, page_width: float) -> Tuple[int, List[str]]:
        """
        Orders text blocks in natural reading order.
        For two-column documents, reads column 1 top-to-bottom, then column 2 top-to-bottom.
        """
        blocks = page.get_text("blocks")
        # Filter for text blocks (type 0)
        text_blocks = [b for b in blocks if len(b) >= 5 and b[4].strip() and b[6] == 0]

        if not text_blocks:
            return 1, []

        midpoint = page_width / 2.0
        # Check if blocks cleanly divide into left and right columns
        left_blocks = [b for b in text_blocks if b[2] <= midpoint + 30]
        right_blocks = [b for b in text_blocks if b[0] >= midpoint - 30]

        is_two_column = (
            len(left_blocks) >= 2 and
            len(right_blocks) >= 2 and
            (len(left_blocks) + len(right_blocks)) >= (len(text_blocks) * 0.8)
        )

        if is_two_column:
            # Sort left column top-to-bottom, then right column top-to-bottom
            left_sorted = sorted(left_blocks, key=lambda b: (b[1], b[0]))
            right_sorted = sorted(right_blocks, key=lambda b: (b[1], b[0]))
            sorted_blocks = left_sorted + right_sorted
            columns = 2
        else:
            # Standard top-to-bottom reading order
            sorted_blocks = sorted(text_blocks, key=lambda b: (b[1], b[0]))
            columns = 1

        ordered_texts = [b[4].strip() for b in sorted_blocks if b[4].strip()]
        return columns, ordered_texts

    def classify_document(
        self,
        document_id: str,
        document_name: str,
        total_pages: int,
        native_pages: int,
        ocr_pages: int,
        empty_pages: int,
        failed_pages: int,
        total_chars: int,
        total_words: int,
        total_tables: int,
        total_headings: int,
        processing_time: float
    ) -> DocumentAnalysis:
        """Determines overall document classification and packages statistics."""
        if total_pages == 0 or (empty_pages + failed_pages) == total_pages:
            doc_type = "empty"
        elif ocr_pages > 0 and native_pages == 0:
            doc_type = "scanned"
        elif ocr_pages > 0 and native_pages > 0:
            doc_type = "hybrid"
        else:
            doc_type = "text_native"

        return DocumentAnalysis(
            document_id=document_id,
            document_name=document_name,
            total_pages=total_pages,
            native_text_pages=native_pages,
            ocr_pages=ocr_pages,
            empty_pages=empty_pages,
            failed_pages=failed_pages,
            total_characters=total_chars,
            total_words=total_words,
            total_tables=total_tables,
            total_headings=total_headings,
            document_type=doc_type,
            processing_time_seconds=round(processing_time, 2)
        )

document_analyzer = DocumentAnalyzer()
