"""
rules.py — Cleaning rules
Composable, single-purpose transformations for tabular data. Each rule
implements .apply(df) -> df so they can be chained in a CleaningPipeline
(see pipeline.py). This is the generic version of the ad-hoc cleaning
logic that used to be hardcoded inside tlf_stats.CensusLoader._clean().
"""

from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Union

import pandas as pd


class CleaningRule(ABC):
    """Base class for a single cleaning/transformation step."""

    @abstractmethod
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        ...

    def __repr__(self):
        return f"{self.__class__.__name__}()"


class RenameColumns(CleaningRule):
    """Rename raw source columns to canonical names."""

    def __init__(self, column_map: Dict[str, str]):
        self.column_map = column_map

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.rename(columns=self.column_map)


class StripWhitespace(CleaningRule):
    """Strip leading/trailing whitespace from string columns."""

    def __init__(self, columns: Optional[List[str]] = None):
        self.columns = columns

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        cols = self.columns or list(df.select_dtypes(include=["object", "string"]).columns)
        for col in cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        return df


class CoerceNumeric(CleaningRule):
    """
    Convert columns to numeric, first stripping thousands separators and
    stray whitespace (common in PDF-extracted tables). Values that still
    can't be parsed become NaN.
    """

    def __init__(self, columns: List[str], errors: str = "coerce"):
        self.columns = columns
        self.errors = errors

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in self.columns:
            if col in df.columns:
                cleaned = (
                    df[col].astype(str)
                    .str.replace(",", "", regex=False)
                    .str.replace(" ", "", regex=False)
                )
                df[col] = pd.to_numeric(cleaned, errors=self.errors)
        return df


class DropDuplicates(CleaningRule):
    """Remove duplicate rows, optionally scoped to a subset of columns."""

    def __init__(self, subset: Optional[List[str]] = None, keep: str = "first"):
        self.subset = subset
        self.keep = keep

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.drop_duplicates(subset=self.subset, keep=self.keep).reset_index(drop=True)


class DropMissing(CleaningRule):
    """Drop rows with missing values in the given columns (or any column if None)."""

    def __init__(self, columns: Optional[List[str]] = None):
        self.columns = columns

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.dropna(subset=self.columns).reset_index(drop=True)


class FillMissing(CleaningRule):
    """Fill missing values in the given columns via a fixed value or a column statistic."""

    def __init__(self, columns: List[str], strategy: Union[str, float, int] = "mean"):
        self.columns = columns
        self.strategy = strategy

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in self.columns:
            if col not in df.columns:
                continue
            if self.strategy == "mean":
                df[col] = df[col].fillna(df[col].mean())
            elif self.strategy == "median":
                df[col] = df[col].fillna(df[col].median())
            elif self.strategy == "zero":
                df[col] = df[col].fillna(0)
            else:
                df[col] = df[col].fillna(self.strategy)
        return df


class DropRowsWhere(CleaningRule):
    """Drop rows matching a predicate, e.g. negative population values."""

    def __init__(self, predicate: Callable[[pd.DataFrame], pd.Series]):
        """predicate(df) must return a boolean Series — True marks a row for removal."""
        self.predicate = predicate

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        drop_mask = self.predicate(df)
        return df[~drop_mask].reset_index(drop=True)
