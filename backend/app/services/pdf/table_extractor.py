import logging
from typing import List, Optional
import pymupdf

from app.schemas.universal_pdf import TableData

logger = logging.getLogger(__name__)

class TableExtractor:
    """
    Extracts structured tables from PDF pages using PyMuPDF's page.find_tables().
    Preserves cell hierarchies, column headers, row alignments, and outputs clean Markdown tables.
    """

    def extract_tables_from_page(self, page: pymupdf.Page, page_number: int) -> List[TableData]:
        """
        Locates and extracts all tables on a given page.
        
        Args:
            page: PyMuPDF Page
            page_number: 1-based page number
            
        Returns:
            List of structured TableData objects
        """
        extracted_tables: List[TableData] = []

        try:
            tabs = page.find_tables()
            if not tabs or tabs.tables is None:
                return []

            for idx, tab in enumerate(tabs.tables):
                raw_data = tab.extract()
                if not raw_data or len(raw_data) == 0:
                    continue

                # Header detection: First row is treated as header if valid, otherwise fallback
                first_row = [self._clean_cell(c) for c in raw_data[0]]
                
                if len(raw_data) > 1:
                    headers = first_row
                    rows = [[self._clean_cell(c) for c in r] for r in raw_data[1:]]
                else:
                    # Single row table
                    headers = [f"Col {i+1}" for i in range(len(first_row))]
                    rows = [first_row]

                # Ensure uniform column count
                col_count = max(len(headers), max((len(r) for r in rows), default=0))
                # Pad headers if necessary
                while len(headers) < col_count:
                    headers.append(f"Col {len(headers)+1}")

                # Pad rows if necessary
                padded_rows: List[List[str]] = []
                for r in rows:
                    row_copy = list(r)
                    while len(row_copy) < col_count:
                        row_copy.append("")
                    padded_rows.append(row_copy)

                markdown = self.generate_markdown(headers, padded_rows)

                bbox = list(tab.bbox) if hasattr(tab, "bbox") and tab.bbox else []

                extracted_tables.append(TableData(
                    page_number=page_number,
                    table_index=idx,
                    bbox=bbox,
                    headers=headers,
                    rows=padded_rows,
                    markdown=markdown,
                    row_count=len(padded_rows),
                    col_count=col_count
                ))

            return extracted_tables

        except Exception as e:
            logger.warning(f"Table extraction encountered an issue on page {page_number}: {e}")
            return []

    def _clean_cell(self, cell_content: Optional[str]) -> str:
        """Cleans internal newlines and whitespace within a table cell."""
        if cell_content is None:
            return ""
        # Flatten newlines to keep markdown table row intact
        cleaned = str(cell_content).replace("\r", " ").replace("\n", " ").strip()
        # Escape pipe symbols in markdown
        cleaned = cleaned.replace("|", "\\|")
        return cleaned

    def generate_markdown(self, headers: List[str], rows: List[List[str]]) -> str:
        """Converts structured table headers and rows to GitHub-flavored Markdown table."""
        if not headers and not rows:
            return ""

        header_line = "| " + " | ".join(h if h else " " for h in headers) + " |"
        separator_line = "| " + " | ".join("---" for _ in headers) + " |"

        row_lines = []
        for r in rows:
            row_lines.append("| " + " | ".join(c if c else " " for c in r) + " |")

        return "\n".join([header_line, separator_line] + row_lines)

table_extractor = TableExtractor()
