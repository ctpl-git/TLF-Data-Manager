"""
extract.py — PDFTableExtractor
Pulls raw tables out of PDF reports (e.g. government census PDFs) into
pandas DataFrames. No cleaning or normalization is applied here — that
is the job of rules.py / pipeline.py. Keeping extraction and cleaning
separate means a messy source PDF never forces messy assumptions into
the transformation logic.

Three things this module deliberately handles for large, multi-page
government reports (e.g. a 2000+ page census PDF):

1. Header-per-section, not header-per-page. Many such PDFs print the
   column header once, then continue the same table across many pages
   with no header repeated. Treating "first row on this page" as the
   header (the naive approach) silently eats a real data row as if it
   were column names on every continuation page. Pass `known_header`
   once you know the fixed schema (e.g. from the first page) and every
   row on every requested page is treated as data.

2. Cost of opening the PDF. Accessing `pdfplumber.PDF.pages` (via
   `len()` or indexing) walks the whole page tree once, which is slow
   on a document with thousands of pages. Calling `extract_page()` in
   a loop reopens the file and re-triggers that walk on every single
   iteration. `extract_pages()` opens the file exactly once for a
   whole batch of pages — use it instead of looping `extract_page()`
   for anything more than a couple of pages.

3. Visibility into skipped rows. A row whose cell count doesn't match
   the header is dropped rather than crashing or misaligning columns.
   On a large batch that count can get big fast (page furniture,
   wrapped multi-line cells, footnotes) — `last_skipped_rows` alone
   doesn't tell you whether that's expected noise or real data loss.
   `last_skipped_samples` and `last_skipped_by_page` let you actually
   look at what got dropped instead of guessing.
"""

from pathlib import Path
from typing import List, Optional

import pandas as pd
import pdfplumber

MAX_SKIPPED_SAMPLES = 50  # cap so a huge skip count doesn't blow up memory


class PDFTableExtractor:
    """
    Extracts tables from a PDF file into raw DataFrames.

    Usage (single page, own header on the page):
        extractor = PDFTableExtractor("report.pdf")
        one_table = extractor.extract_page(3)[0]

    Usage (many pages, one shared header known in advance — e.g. a
    census table that only prints its header once and continues over
    hundreds of pages):
        header = [...]  # from inspecting the first page
        tables = extractor.extract_pages(range(1, 51), known_header=header)

    After any extract call, inspect what (if anything) got dropped:
        extractor.last_skipped_rows        # total count
        extractor.last_skipped_by_page     # {page_number: count}
        extractor.last_skipped_samples     # up to 50 (page_number, raw_row) tuples
    """

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"PDF not found: {self.filepath}")
        self.last_skipped_rows = 0
        self.last_skipped_by_page = {}
        self.last_skipped_samples = []

    def page_count(self) -> int:
        with pdfplumber.open(self.filepath) as pdf:
            return len(pdf.pages)

    def extract_page(
        self, page_number: int, table_settings: Optional[dict] = None,
        known_header: Optional[List[str]] = None,
    ) -> List[pd.DataFrame]:
        """
        Extract all tables found on a single page (1-indexed).
        For extracting many pages at once, prefer extract_pages() —
        it only opens the PDF once instead of once per call.
        """
        return self.extract_pages([page_number], table_settings, known_header)

    def extract_all(
        self, table_settings: Optional[dict] = None, known_header: Optional[List[str]] = None,
    ) -> List[pd.DataFrame]:
        """Extract all tables across every page of the PDF, in page order."""
        with pdfplumber.open(self.filepath) as pdf:
            page_numbers = range(1, len(pdf.pages) + 1)
            return self._extract_from_open_pdf(pdf, page_numbers, table_settings, known_header)

    def extract_pages(
        self, page_numbers, table_settings: Optional[dict] = None,
        known_header: Optional[List[str]] = None,
    ) -> List[pd.DataFrame]:
        """
        Extract tables from multiple specific pages in a single PDF open.
        Prefer this over looping extract_page() — on a large PDF, each
        extract_page() call reopens the file and re-walks its page tree,
        which is slow; this walks it exactly once for the whole batch.
        """
        with pdfplumber.open(self.filepath) as pdf:
            total = len(pdf.pages)
            for page_number in page_numbers:
                if page_number < 1 or page_number > total:
                    raise ValueError(f"Page {page_number} out of range (1-{total})")
            return self._extract_from_open_pdf(pdf, page_numbers, table_settings, known_header)

    def _extract_from_open_pdf(self, pdf, page_numbers, table_settings, known_header):
        tables = []
        skipped_total = 0
        skipped_by_page = {}
        skipped_samples = []
        for page_number in page_numbers:
            page = pdf.pages[page_number - 1]
            page_tables, page_skipped, page_samples = self._tables_from_page(
                page, table_settings, known_header
            )
            tables.extend(page_tables)
            if page_skipped:
                skipped_total += page_skipped
                skipped_by_page[page_number] = page_skipped
                for sample_row in page_samples:
                    if len(skipped_samples) < MAX_SKIPPED_SAMPLES:
                        skipped_samples.append((page_number, sample_row))

        self.last_skipped_rows = skipped_total
        self.last_skipped_by_page = skipped_by_page
        self.last_skipped_samples = skipped_samples
        return tables

    @staticmethod
    def _looks_like_header(row, columns) -> bool:
        """True if `row` is (case/whitespace-insensitively) the header itself."""
        if len(row) != len(columns):
            return False
        return all(
            str(cell).strip().lower() == str(col).strip().lower()
            for cell, col in zip(row, columns)
        )

    @classmethod
    def _tables_from_page(cls, page, table_settings: Optional[dict], known_header: Optional[List[str]]):
        """Returns (dataframes, skipped_count, sample_skipped_rows) for one page."""
        raw_tables = page.extract_tables(table_settings or {})
        result = []
        skipped = 0
        samples = []
        for raw in raw_tables:
            if not raw:
                continue
            if known_header is not None:
                columns = known_header
                # A page may or may not repeat the header; only strip it if
                # it's actually there — most continuation pages won't be.
                if cls._looks_like_header(raw[0], columns):
                    rows = raw[1:]
                else:
                    rows = raw
            else:
                if len(raw) < 2:
                    continue  # no header + data row present
                header, *rows = raw
                columns = header

            # Defend against rows with a different cell count than the header
            # (merged/split cells, ragged extraction) rather than letting
            # pandas raise or silently misalign columns.
            good_rows = []
            for r in rows:
                if len(r) == len(columns):
                    good_rows.append(r)
                else:
                    skipped += 1
                    if len(samples) < MAX_SKIPPED_SAMPLES:
                        samples.append(r)
            if good_rows:
                result.append(pd.DataFrame(good_rows, columns=columns))
        return result, skipped, samples

    def print_skip_diagnostics(self, max_samples: int = 20):
        """Print a readable summary of what got skipped on the last extract call."""
        if not self.last_skipped_rows:
            print("No rows skipped.")
            return
        print(f"Skipped {self.last_skipped_rows} row(s) total.")
        pages_affected = sorted(self.last_skipped_by_page)
        print(f"Affected {len(pages_affected)} page(s). Worst pages: "
              f"{sorted(self.last_skipped_by_page.items(), key=lambda kv: -kv[1])[:5]}")
        print(f"\nSample skipped rows (up to {max_samples}):")
        for page_number, row in self.last_skipped_samples[:max_samples]:
            print(f"  page {page_number} ({len(row)} cells): {row}")
