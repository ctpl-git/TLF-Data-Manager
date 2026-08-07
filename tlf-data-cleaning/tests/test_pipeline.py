import os
import pandas as pd
import pytest

from tlf_data_cleaning.pipeline import CleaningPipeline
from tlf_data_cleaning.rules import (
    RenameColumns,
    StripWhitespace,
    CoerceNumeric,
    DropDuplicates,
)

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_census_table.pdf")

COLUMN_MAP = {
    "Division": "region",
    "District": "subregion",
    "Total Population": "total_population",
    "Male": "male",
    "Female": "female",
    "Households": "households",
    "Urban Population": "urban_population",
    "Rural Population": "rural_population",
    "Literacy Rate": "literacy_rate",
    "Avg HH Size": "avg_household_size",
}

NUMERIC_COLS = [
    "total_population", "male", "female", "households",
    "urban_population", "rural_population", "literacy_rate", "avg_household_size",
]


def make_pipeline():
    return CleaningPipeline([
        RenameColumns(COLUMN_MAP),
        StripWhitespace(columns=["region", "subregion"]),
        CoerceNumeric(NUMERIC_COLS),
        DropDuplicates(subset=["region", "subregion"]),
    ])


class TestCleaningPipelineFromDataFrame:
    def test_run_produces_canonical_columns(self):
        raw = pd.DataFrame({
            "Division": [" Dhaka", "Dhaka "],
            "District": ["Dhaka ", " Gazipur"],
            "Total Population": ["12,043,977", "5,008,768"],
            "Male": ["6,221,452", "2,554,472"],
            "Female": ["5,822,525", "2,454,296"],
            "Households": ["2,891,760", "1,140,420"],
            "Urban Population": ["10,437,210", "2,750,230"],
            "Rural Population": ["1,606,767", "2,258,538"],
            "Literacy Rate": ["79.8", "74.2"],
            "Avg HH Size": ["4.15", "4.30"],
        })
        pipeline = make_pipeline()
        clean = pipeline.run(raw)
        assert list(clean.columns) == [
            "region", "subregion", "total_population", "male", "female", "households",
            "urban_population", "rural_population", "literacy_rate", "avg_household_size",
        ]
        assert clean["region"].iloc[0] == "Dhaka"
        assert clean["total_population"].iloc[0] == 12043977

    def test_quality_report_available_after_run(self):
        raw = pd.DataFrame({
            "Division": ["Dhaka"], "District": ["Dhaka"],
            "Total Population": ["1,000"], "Male": ["500"], "Female": ["500"],
            "Households": ["200"], "Urban Population": ["100"], "Rural Population": ["900"],
            "Literacy Rate": ["80.0"], "Avg HH Size": ["4.2"],
        })
        pipeline = make_pipeline()
        pipeline.run(raw)
        report = pipeline.quality_report()
        summary = report.summary()
        assert summary["row_count"] == 1

    def test_quality_report_before_run_raises(self):
        pipeline = make_pipeline()
        with pytest.raises(RuntimeError):
            pipeline.quality_report()


class TestCleaningPipelineFromPDF:
    def test_run_from_pdf_end_to_end(self):
        pipeline = make_pipeline()
        clean = pipeline.run_from_pdf(FIXTURE, page=1)

        # Duplicate Cox's Bazar row (identical on region+subregion) collapsed.
        assert len(clean) == 5
        assert set(clean.columns) == {
            "region", "subregion", "total_population", "male", "female", "households",
            "urban_population", "rural_population", "literacy_rate", "avg_household_size",
        }
        # Thousands separators resolved to real numbers.
        dhaka_row = clean[(clean["region"] == "Dhaka") & (clean["subregion"] == "Dhaka")]
        assert dhaka_row["total_population"].iloc[0] == 12043977
        # Whitespace from the PDF ("District ", " Chattogram ") resolved.
        assert "Chattogram" in clean["subregion"].values

    def test_run_from_pdf_and_export(self, tmp_path):
        pipeline = make_pipeline()
        out_path = tmp_path / "bangladesh_clean.csv"
        clean = pipeline.run_from_pdf_and_export(FIXTURE, page=1, output_path=str(out_path))
        assert out_path.exists()
        reloaded = pd.read_csv(out_path)
        assert len(reloaded) == len(clean)
        assert "region" in reloaded.columns

    def test_invalid_table_index_raises(self):
        pipeline = make_pipeline()
        with pytest.raises(ValueError):
            pipeline.run_from_pdf(FIXTURE, page=1, table_index=5)
