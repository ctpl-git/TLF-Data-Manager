"""
tlf-data-cleaning
-----------------
Data extraction, transformation, normalization, deduplication, and
quality-check pipelines for the TLF ecosystem. Implements the
`tlf-data-cleaning` package described in the TLF-Data-Manager README.

Typical use: extract a raw table out of a government census PDF, then
run it through a CleaningPipeline of composable rules to produce the
canonical, per-country schema that tlf-census-stats expects (region/subregion
+ standard numeric fields), plus a quality report on the result.
"""

from .extract import PDFTableExtractor
from .rules import (
    CleaningRule,
    RenameColumns,
    StripWhitespace,
    CoerceNumeric,
    DropDuplicates,
    DropMissing,
    FillMissing,
    DropRowsWhere,
)
from .quality import QualityReport
from .pipeline import CleaningPipeline

__all__ = [
    "PDFTableExtractor",
    "CleaningRule",
    "RenameColumns",
    "StripWhitespace",
    "CoerceNumeric",
    "DropDuplicates",
    "DropMissing",
    "FillMissing",
    "DropRowsWhere",
    "QualityReport",
    "CleaningPipeline",
]

__version__ = "0.1.0"
