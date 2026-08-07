import os
import pytest

from tlf_data_cleaning.extract import PDFTableExtractor

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_census_table.pdf")


class TestPDFTableExtractor:
    def test_invalid_path_raises(self):
        with pytest.raises(FileNotFoundError):
            PDFTableExtractor("nonexistent.pdf")

    def test_page_count(self):
        extractor = PDFTableExtractor(FIXTURE)
        assert extractor.page_count() >= 1

    def test_extract_page_returns_table(self):
        extractor = PDFTableExtractor(FIXTURE)
        tables = extractor.extract_page(1)
        assert len(tables) == 1
        df = tables[0]
        assert "Division" in df.columns
        assert len(df) == 6  # 5 unique rows + 1 intentional duplicate in the fixture

    def test_extract_page_out_of_range_raises(self):
        extractor = PDFTableExtractor(FIXTURE)
        with pytest.raises(ValueError):
            extractor.extract_page(99)

    def test_extract_all_matches_extract_page(self):
        extractor = PDFTableExtractor(FIXTURE)
        all_tables = extractor.extract_all()
        page_tables = extractor.extract_page(1)
        assert len(all_tables) == len(page_tables)

    def test_raw_values_are_unprocessed(self):
        """Extraction should not clean anything — that's rules.py's job."""
        extractor = PDFTableExtractor(FIXTURE)
        df = extractor.extract_page(1)[0]
        # Thousands separators and stray whitespace should still be present.
        assert "," in df["Total Population"].iloc[0]
