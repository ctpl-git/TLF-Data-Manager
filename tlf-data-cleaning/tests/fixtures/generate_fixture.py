"""
generate_fixture.py — builds sample_census_table.pdf
Run once (or whenever the fixture needs regenerating):
    python tests/fixtures/generate_fixture.py

Produces a PDF with a table that mimics real government census PDFs:
thousands separators in numbers, inconsistent whitespace, a duplicate
row, and a header row using country-specific admin labels.
"""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

OUTPUT = Path(__file__).parent / "sample_census_table.pdf"

HEADER = ["Division", "District ", "Total Population", "Male", "Female", "Households",
          "Urban Population", "Rural Population", "Literacy Rate", "Avg HH Size"]

# Intentionally messy: thousands separators, stray whitespace, a duplicate row.
ROWS = [
    ["Dhaka", " Dhaka", "12,043,977", "6,221,452", "5,822,525", "2,891,760", "10,437,210", "1,606,767", "79.8", "4.15"],
    ["Dhaka", "Gazipur ", "5,008,768", "2,554,472", "2,454,296", "1,140,420", "2,750,230", "2,258,538", "74.2", "4.30"],
    ["Chattogram", " Chattogram ", "8,235,800", "4,212,310", "4,023,490", "1,876,340", "3,502,190", "4,733,610", "76.4", "4.42"],
    ["Chattogram", "Cox's Bazar", "2,891,726", "1,465,210", "1,426,516", "610,230", "412,870", "2,478,856", "58.6", "4.60"],
    ["Chattogram", "Cox's Bazar", "2,891,726", "1,465,210", "1,426,516", "610,230", "412,870", "2,478,856", "58.6", "4.60"],  # duplicate row
    ["Rajshahi", "Rajshahi", "2,812,335", "1,420,310", "1,392,025", "650,210", "912,340", "1,899,995", "77.9", "4.28"],
]


def build():
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4)
    table_data = [HEADER] + ROWS
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E4053")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
    ]))
    elements = [
        Paragraph("Population and Housing Census 2022 — District Report (sample fixture)", styles["Title"]),
        Spacer(1, 12),
        table,
    ]
    doc.build(elements)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    build()
