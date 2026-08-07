"""
quality.py — QualityReport
Runs data-quality checks over a DataFrame and produces a summary,
independent of whatever cleaning rules were (or weren't) applied to it.
"""

from typing import List, Optional

import pandas as pd


class QualityReport:
    """
    Usage:
        report = QualityReport(df)
        print(report.summary())
        print(report.missing_values())
        print(report.negative_values(["total_population"]))
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def missing_values(self) -> pd.Series:
        """Count of missing values per column."""
        return self.df.isnull().sum()

    def duplicate_count(self, subset: Optional[List[str]] = None) -> int:
        """Number of duplicate rows (optionally scoped to a subset of columns)."""
        return int(self.df.duplicated(subset=subset).sum())

    def negative_values(self, columns: List[str]) -> pd.DataFrame:
        """Rows where any of the given numeric columns is negative."""
        mask = pd.Series(False, index=self.df.index)
        for col in columns:
            if col in self.df.columns:
                mask = mask | (self.df[col] < 0)
        return self.df[mask]

    def summary(self) -> dict:
        """High-level quality snapshot: row/column counts, missing totals, duplicates."""
        missing = self.missing_values()
        return {
            "row_count": len(self.df),
            "column_count": len(self.df.columns),
            "total_missing_values": int(missing.sum()),
            "columns_with_missing": list(missing[missing > 0].index),
            "duplicate_rows": self.duplicate_count(),
        }
