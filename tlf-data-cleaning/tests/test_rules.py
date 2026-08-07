import pandas as pd
import pytest

from tlf_data_cleaning.rules import (
    RenameColumns,
    StripWhitespace,
    CoerceNumeric,
    DropDuplicates,
    DropMissing,
    FillMissing,
    DropRowsWhere,
)


@pytest.fixture
def messy_df():
    return pd.DataFrame({
        "Division": [" Dhaka", "Dhaka ", "Chattogram", "Chattogram"],
        "District": ["Dhaka ", " Gazipur", "Chattogram", "Chattogram"],
        "Total Population": ["12,043,977", "5,008,768", "-100", "-100"],
        "Literacy Rate": [79.8, None, 76.4, 76.4],
    })


class TestRenameColumns:
    def test_renames(self, messy_df):
        rule = RenameColumns({"Division": "region", "District": "subregion"})
        result = rule.apply(messy_df)
        assert "region" in result.columns
        assert "subregion" in result.columns
        assert "Division" not in result.columns


class TestStripWhitespace:
    def test_strips_all_object_columns_by_default(self, messy_df):
        rule = StripWhitespace()
        result = rule.apply(messy_df)
        assert result["Division"].iloc[0] == "Dhaka"
        assert result["District"].iloc[0] == "Dhaka"

    def test_strips_only_given_columns(self, messy_df):
        rule = StripWhitespace(columns=["Division"])
        result = rule.apply(messy_df)
        assert result["Division"].iloc[0] == "Dhaka"
        assert result["District"].iloc[0] == "Dhaka "  # untouched


class TestCoerceNumeric:
    def test_strips_thousands_separators(self, messy_df):
        rule = CoerceNumeric(["Total Population"])
        result = rule.apply(messy_df)
        assert result["Total Population"].iloc[0] == 12043977
        assert result["Total Population"].dtype.kind in "if"

    def test_unparseable_becomes_nan(self):
        df = pd.DataFrame({"x": ["12", "abc", "34"]})
        result = CoerceNumeric(["x"]).apply(df)
        assert pd.isna(result["x"].iloc[1])


class TestDropDuplicates:
    def test_removes_exact_duplicate_rows(self, messy_df):
        clean = StripWhitespace().apply(messy_df)
        result = DropDuplicates().apply(clean)
        assert len(result) == 3  # one of the two Chattogram rows removed

    def test_subset_scoped(self, messy_df):
        clean = StripWhitespace().apply(messy_df)
        result = DropDuplicates(subset=["Division"]).apply(clean)
        assert len(result) == 2  # Dhaka, Chattogram


class TestDropMissing:
    def test_drops_rows_with_missing_values(self, messy_df):
        result = DropMissing(columns=["Literacy Rate"]).apply(messy_df)
        assert len(result) == 3
        assert result["Literacy Rate"].isnull().sum() == 0


class TestFillMissing:
    def test_fills_with_zero(self, messy_df):
        result = FillMissing(["Literacy Rate"], strategy="zero").apply(messy_df)
        assert result["Literacy Rate"].isnull().sum() == 0
        assert result["Literacy Rate"].iloc[1] == 0

    def test_fills_with_mean(self, messy_df):
        result = FillMissing(["Literacy Rate"], strategy="mean").apply(messy_df)
        assert result["Literacy Rate"].isnull().sum() == 0


class TestDropRowsWhere:
    def test_drops_rows_matching_predicate(self, messy_df):
        numeric = CoerceNumeric(["Total Population"]).apply(messy_df)
        result = DropRowsWhere(lambda df: df["Total Population"] < 0).apply(numeric)
        assert (result["Total Population"] >= 0).all()
