# tlf-data-cleaning

Data extraction, transformation, normalization, deduplication, and quality-check pipelines for the TLF ecosystem — the `tlf-data-cleaning` package described in the [TLF-Data-Manager](https://github.com/ctpl-git/TLF-Data-Manager) README, built out as a real, installable, tested package.

It solves a concrete problem: government census reports (Bangladesh BBS, Pakistan PBS, etc.) are published as PDFs, not clean CSVs. This package extracts the raw tables out of those PDFs and runs them through a composable set of cleaning rules to produce the canonical schema that `tlf-census-stats` expects — without hardcoding any of that cleaning logic inside the stats package itself.

## Install

```bash
pip install -e .
# or, for running the test suite too:
pip install -e ".[dev]"
```

## Modules

| Module | Responsibility |
|---|---|
| `extract.py` | `PDFTableExtractor` — pulls raw tables out of a PDF, no cleaning applied. |
| `rules.py` | Composable `CleaningRule` steps: rename, strip whitespace, coerce numeric, dedupe, drop/fill missing, drop-by-predicate. |
| `pipeline.py` | `CleaningPipeline` — chains rules together, optionally starting from a PDF, and can export straight to CSV. |
| `quality.py` | `QualityReport` — missing values, duplicate rows, negative-value checks, summary snapshot. |

## Quick example: PDF → clean CSV

```python
from tlf_data_cleaning import (
    CleaningPipeline, RenameColumns, StripWhitespace, CoerceNumeric, DropDuplicates,
)

pipeline = CleaningPipeline([
    RenameColumns({"Division": "region", "District": "subregion",
                   "Total Population": "total_population", "Male": "male",
                   "Female": "female", "Households": "households",
                   "Literacy Rate": "literacy_rate"}),
    StripWhitespace(columns=["region", "subregion"]),
    CoerceNumeric(["total_population", "male", "female", "households", "literacy_rate"]),
    DropDuplicates(subset=["region", "subregion"]),
])

clean_df = pipeline.run_from_pdf("bbs_district_report.pdf", page=12)
print(pipeline.quality_report().summary())

pipeline.run_and_export(clean_df, "data/sample/bangladesh_census_2022.csv")
```

## Canonical schema

`tlf-census-stats`'s `CensusLoader` expects data in this shape (see its `country_profiles.py` for exact per-country column aliases):

| Column | Required? | Notes |
|---|---|---|
| `region` | Yes | e.g. Division/Province/State |
| `subregion` | Yes | e.g. District |
| `total_population` | Yes | |
| `male` | Yes | |
| `female` | Yes | |
| `households` | Yes | |
| `urban_population` | Optional | |
| `rural_population` | Optional | |
| `literacy_rate` | Optional | |
| `avg_household_size` | Optional | |
| `third_gender` | Optional | A country's non-binary census category (e.g. Bangladesh's "Hijra"). Not every country publishes this. |

This package is the upstream step for two of the three ways data reaches `tlf-census-stats` — it turns a raw government PDF into a CSV in this same shape.

## Three ways to get data into tlf-census-stats

**1. Already-clean CSV/Excel/JSON — skip this package entirely**

If your source is already a clean spreadsheet/CSV/JSON in (or close to) the canonical shape above, just hand it straight to `CensusLoader` — this package isn't needed at all:

```python
from tlf_census_stats import CensusLoader
df = CensusLoader("already_clean_bangladesh_census.csv", country="bangladesh").load()
```

**2. Flat-country PDF (e.g. Bangladesh, Pakistan) — this package handles the whole thing**

Most countries' census PDFs are a flat table per page — extract, clean, and hand off directly:

```python
from tlf_data_cleaning import (
    CleaningPipeline, RenameColumns, StripWhitespace, CoerceNumeric, DropDuplicates,
)
from tlf_census_stats import CensusLoader, StatsReporter

# 1. PDF -> clean CSV (this package)
pipeline = CleaningPipeline([
    RenameColumns({"Division": "region", "District": "subregion",
                   "Total Population": "total_population", "Male": "male",
                   "Female": "female", "Households": "households",
                   "Literacy Rate": "literacy_rate"}),
    StripWhitespace(columns=["region", "subregion"]),
    CoerceNumeric(["total_population", "male", "female", "households", "literacy_rate"]),
    DropDuplicates(subset=["region", "subregion"]),
])
pipeline.run_from_pdf_and_export(
    "bbs_district_report.pdf", page=12,
    output_path="data/sample/bangladesh_census_2022.csv",
)

# 2. clean CSV -> stats report (tlf-census-stats)
reporter = StatsReporter("data/sample/bangladesh_census_2022.csv", country="bangladesh")
reporter.run()
```

**3. India's hierarchical PDF layout — extract here, transform in tlf-census-stats**

India's census PDF has a nested INDIA → STATE → DISTRICT → SUB-DISTRICT structure that a generic `CleaningPipeline` of rename/strip/coerce rules can't reshape — that's what `tlf-census-stats`'s `IndiaCensusTransformer` is specifically for. This package only does the raw extraction step; the reshaping happens on the other side:

```python
from tlf_data_cleaning import PDFTableExtractor
from tlf_census_stats import IndiaCensusTransformer, CensusLoader, StatsReporter

# 1. Extract raw tables (this package) — no cleaning/reshaping applied
extractor = PDFTableExtractor("india_2011.pdf")
tables = extractor.extract_pages(range(1, 2226), known_header=IndiaCensusTransformer.EXPECTED_HEADER)

# 2. Reshape the hierarchical rows into canonical region/subregion rows (tlf-census-stats)
df = IndiaCensusTransformer().transform(tables)
df.to_csv("data/sample/india_from_pdf.csv", index=False)

# 3. Analyze (tlf-census-stats)
reporter = StatsReporter("data/sample/india_from_pdf.csv", country="india")
reporter.run()
```

Column names produced by workflow 2's pipeline just need to match the canonical schema table above for a given country's profile — workflow 3 doesn't need column renaming at all, since `IndiaCensusTransformer` already outputs canonical column names directly.

## Notes on real government PDFs

- `pdfplumber`'s table detection works well on ruled/gridded tables (like the BBS district reports) but can miss tables with no visible borders — pass `table_settings` to `extract_page`/`extract_all` to tune detection (see pdfplumber's docs for `vertical_strategy` / `horizontal_strategy` options) if a specific report doesn't extract cleanly.
- Multi-line headers or footnote rows sometimes get pulled in as data rows — inspect `extractor.extract_page(n)` output before wiring it into a `CleaningPipeline`, and add a `DropRowsWhere` rule to filter out any non-data rows if needed.

## Tests

```bash
python -m pytest tests/ -v
```

`tests/fixtures/generate_fixture.py` builds the sample PDF used by the test suite — a small table with thousands separators, stray whitespace, and a duplicate row, mimicking real BBS/PBS-style reports.
Regenerate it with:

```bash
python tests/fixtures/generate_fixture.py
```