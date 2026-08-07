import pandas as pd
import pytest

from tlf_data_cleaning.quality import QualityReport


@pytest.fixture
def df():
    return pd.DataFrame({
        "region": ["Dhaka", "Dhaka", "Chattogram", "Chattogram"],
        "subregion": ["Dhaka", "Gazipur", "Chattogram", "Chattogram"],
        "total_population": [12043977, 5008768, -100, -100],
        "literacy_rate": [79.8, None, 76.4, 76.4],
    })


class TestQualityReport:
    def test_missing_values(self, df):
        report = QualityReport(df)
        missing = report.missing_values()
        assert missing["literacy_rate"] == 1

    def test_duplicate_count(self, df):
        report = QualityReport(df)
        assert report.duplicate_count() == 1

    def test_duplicate_count_subset(self, df):
        report = QualityReport(df)
        assert report.duplicate_count(subset=["region"]) == 2

    def test_negative_values(self, df):
        report = QualityReport(df)
        negatives = report.negative_values(["total_population"])
        assert len(negatives) == 2

    def test_summary_keys(self, df):
        report = QualityReport(df)
        summary = report.summary()
        assert summary["row_count"] == 4
        assert summary["duplicate_rows"] == 1
        assert "literacy_rate" in summary["columns_with_missing"]
