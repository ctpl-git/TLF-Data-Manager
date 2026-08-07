"""
pipeline.py — CleaningPipeline
Chains cleaning rules together and, optionally, runs a PDF extraction
step first — so a raw government PDF table can become a clean,
canonical CSV in one call.
"""

from typing import List, Optional

import pandas as pd

from .extract import PDFTableExtractor
from .quality import QualityReport
from .rules import CleaningRule


class CleaningPipeline:
    """
    Usage (already-extracted / raw DataFrame):
        pipeline = CleaningPipeline([
            RenameColumns({"Division": "region", "District": "subregion"}),
            StripWhitespace(),
            CoerceNumeric(["total_population", "male", "female"]),
            DropDuplicates(),
        ])
        clean_df = pipeline.run(raw_df)

    Usage (starting from a PDF):
        clean_df = pipeline.run_from_pdf("report.pdf", page=4)
    """

    def __init__(self, rules: List[CleaningRule]):
        self.rules = rules
        self._last_quality_report: Optional[QualityReport] = None

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all rules in sequence to a raw DataFrame."""
        for rule in self.rules:
            df = rule.apply(df)
        self._last_quality_report = QualityReport(df)
        return df

    def run_from_pdf(self, filepath: str, page: int, table_index: int = 0) -> pd.DataFrame:
        """Extract one table from a PDF page, then run the cleaning rules on it."""
        extractor = PDFTableExtractor(filepath)
        tables = extractor.extract_page(page)
        if table_index >= len(tables):
            raise ValueError(
                f"Page {page} has {len(tables)} table(s); table_index {table_index} out of range"
            )
        return self.run(tables[table_index])

    def quality_report(self) -> QualityReport:
        """Quality report for the result of the most recent run()/run_from_pdf() call."""
        if self._last_quality_report is None:
            raise RuntimeError("Run the pipeline before requesting a quality report.")
        return self._last_quality_report

    def run_and_export(self, df: pd.DataFrame, output_path: str) -> pd.DataFrame:
        """Run cleaning rules and write the result straight to a CSV file."""
        clean_df = self.run(df)
        clean_df.to_csv(output_path, index=False)
        return clean_df

    def run_from_pdf_and_export(self, filepath: str, page: int, output_path: str, table_index: int = 0) -> pd.DataFrame:
        """Extract a table from a PDF, clean it, and write the result to a CSV file."""
        clean_df = self.run_from_pdf(filepath, page, table_index=table_index)
        clean_df.to_csv(output_path, index=False)
        return clean_df
