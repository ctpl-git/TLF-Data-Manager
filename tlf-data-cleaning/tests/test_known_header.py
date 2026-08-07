import os
import pytest

from tlf_data_cleaning.extract import PDFTableExtractor

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "india_census_sample.pdf")

HEADER = [
    "India/ State/ Union Territory/ District/ Sub-district", "Name",
    "Total/ Rural/ Urban", "Number of households", "Total Population",
    "Male Population", "Female Population", "Area (In sq. km)",
]


class TestKnownHeaderContinuation:
    def test_naive_extraction_eats_a_data_row_as_header_on_continuation_page(self):
        """Documents the bug: without known_header, a headerless page 2
        misreads its first data row as column names."""
        extractor = PDFTableExtractor(FIXTURE)
        page2_tables = extractor.extract_page(2)
        # The first data row ("SUB-DISTRICT", "Kupwara", "Urban", ...)
        # got consumed as a header instead of a real header.
        assert page2_tables[0].columns.tolist()[0] == "SUB-DISTRICT"

    def test_known_header_strips_real_header_on_page_with_one(self):
        extractor = PDFTableExtractor(FIXTURE)
        tables = extractor.extract_pages([1], known_header=HEADER)
        df = tables[0]
        assert list(df.columns) == HEADER
        assert len(df) == 5  # 5 data rows on page 1, header row correctly excluded
        assert df.iloc[0]["India/ State/ Union Territory/ District/ Sub-district"] == "INDIA"

    def test_known_header_keeps_all_rows_on_headerless_page(self):
        extractor = PDFTableExtractor(FIXTURE)
        tables = extractor.extract_pages([2], known_header=HEADER)
        df = tables[0]
        assert list(df.columns) == HEADER
        assert len(df) == 5  # all 5 rows on page 2 are data — none should be dropped as a header
        assert df.iloc[0]["India/ State/ Union Territory/ District/ Sub-district"] == "SUB-DISTRICT"

    def test_extract_pages_spans_both_pages_correctly(self):
        extractor = PDFTableExtractor(FIXTURE)
        tables = extractor.extract_pages([1, 2], known_header=HEADER)
        total_rows = sum(len(t) for t in tables)
        assert total_rows == 10  # 5 real rows per page, no header rows counted as data
        assert extractor.last_skipped_rows == 0

    def test_extract_pages_out_of_range_raises(self):
        extractor = PDFTableExtractor(FIXTURE)
        with pytest.raises(ValueError):
            extractor.extract_pages([1, 99], known_header=HEADER)

    def test_extract_page_delegates_to_extract_pages(self):
        """extract_page(n) should behave identically to extract_pages([n])."""
        extractor = PDFTableExtractor(FIXTURE)
        single = extractor.extract_page(2, known_header=HEADER)
        batch = extractor.extract_pages([2], known_header=HEADER)
        assert single[0].equals(batch[0])

    def test_extract_pages_opens_the_pdf_only_once(self, monkeypatch):
        """
        The actual bug that hung on a 2000+ page PDF: extract_page() in a loop
        reopens the file (and re-walks its page tree) on every iteration.
        extract_pages() must open it exactly once for the whole batch.
        """
        import pdfplumber
        open_calls = []
        real_open = pdfplumber.open

        def counting_open(*args, **kwargs):
            open_calls.append(1)
            return real_open(*args, **kwargs)

        monkeypatch.setattr(pdfplumber, "open", counting_open)
        extractor = PDFTableExtractor(FIXTURE)
        extractor.extract_pages([1, 2], known_header=HEADER)
        assert len(open_calls) == 1

    def test_looping_extract_page_reopens_per_call(self, monkeypatch):
        """Documents why looping extract_page() is the slow path to avoid."""
        import pdfplumber
        open_calls = []
        real_open = pdfplumber.open

        def counting_open(*args, **kwargs):
            open_calls.append(1)
            return real_open(*args, **kwargs)

        monkeypatch.setattr(pdfplumber, "open", counting_open)
        extractor = PDFTableExtractor(FIXTURE)
        for page in [1, 2]:
            extractor.extract_page(page, known_header=HEADER)
        assert len(open_calls) == 2


class FakePage:
    """Minimal stand-in for a pdfplumber Page — lets skip-diagnostics tests
    be deterministic and fast instead of depending on PDF rendering quirks."""

    def __init__(self, raw_tables):
        self._raw_tables = raw_tables

    def extract_tables(self, settings=None):
        return self._raw_tables


class TestSkipDiagnostics:
    SIMPLE_HEADER = ["a", "b", "c"]

    def test_mismatched_rows_are_skipped_and_recorded(self):
        good_row = ["1", "2", "3"]
        short_row = ["1", "2"]           # merged-cell artifact: one column short
        long_row = ["1", "2", "3", "4"]  # split-cell artifact: one column long
        page = FakePage([[good_row, short_row, long_row]])

        dfs, skipped, samples = PDFTableExtractor._tables_from_page(page, None, self.SIMPLE_HEADER)

        assert skipped == 2
        assert len(dfs) == 1 and len(dfs[0]) == 1  # only the good row survived
        assert short_row in samples
        assert long_row in samples

    def test_extract_pages_populates_per_page_and_sample_diagnostics(self, monkeypatch):
        good_row = ["1", "2", "3"]
        short_row = ["1", "2"]

        class FakePDF:
            pages = [FakePage([[good_row, short_row]]), FakePage([[good_row, short_row, short_row]])]

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        import pdfplumber
        monkeypatch.setattr(pdfplumber, "open", lambda *a, **k: FakePDF())

        extractor = PDFTableExtractor(FIXTURE)  # path just needs to exist for __init__
        extractor.extract_pages([1, 2], known_header=self.SIMPLE_HEADER)

        assert extractor.last_skipped_rows == 3
        assert extractor.last_skipped_by_page == {1: 1, 2: 2}
        assert len(extractor.last_skipped_samples) == 3
        assert all(page_num in (1, 2) for page_num, _row in extractor.last_skipped_samples)

    def test_skipped_samples_capped(self, monkeypatch):
        short_row = ["1", "2"]
        many_bad_rows = [short_row] * 100

        class FakePDF:
            pages = [FakePage([many_bad_rows])]

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        import pdfplumber
        monkeypatch.setattr(pdfplumber, "open", lambda *a, **k: FakePDF())

        extractor = PDFTableExtractor(FIXTURE)
        extractor.extract_pages([1], known_header=self.SIMPLE_HEADER)

        assert extractor.last_skipped_rows == 100          # true total, uncapped
        assert len(extractor.last_skipped_samples) == 50   # samples capped for memory safety

    def test_print_skip_diagnostics_no_skips(self, capsys):
        extractor = PDFTableExtractor(FIXTURE)
        extractor.extract_pages([1, 2], known_header=HEADER)  # real fixture, 0 skips
        extractor.print_skip_diagnostics()
        assert "No rows skipped" in capsys.readouterr().out
