"""
generate_india_fixture.py — builds india_census_sample.pdf
Run once (or whenever the fixture needs regenerating):
    python tests/fixtures/generate_india_fixture.py

Mimics the real India Census PDF structure that broke the original
extractor: page 1 has the header row and a STATE + DISTRICT block that
runs out of room mid-SUB-DISTRICT; page 2 has NO header at all and
just continues the same table with more rows (some SUB-DISTRICT, then
a second DISTRICT block). This is what actually happens across
thousands of pages in the real Census 2011 PDF and is exactly the case
`known_header` is for.
"""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

OUTPUT = Path(__file__).parent / "india_census_sample.pdf"

HEADER = [
    "India/ State/ Union Territory/ District/ Sub-district", "Name",
    "Total/ Rural/ Urban", "Number of households", "Total Population",
    "Male Population", "Female Population", "Area (In sq. km)",
]

PAGE1_ROWS = [
    ["INDIA", "INDIA @&", "Total", "249,501,663", "1,210,854,977", "623,270,258", "587,584,719", "3287469.00"],
    ["STATE", "JAMMU & KASHMIR @&", "Total", "2,119,718", "12,541,302", "6,640,662", "5,900,640", "222236.00"],
    ["DISTRICT", "Kupwara", "Total", "113,929", "870,354", "474,190", "396,164", "2379.00"],
    ["SUB-DISTRICT", "Kupwara", "Total", "63,022", "540,914", "297,837", "243,077", "301.94"],
    ["SUB-DISTRICT", "Kupwara", "Rural", "56,014", "465,323", "252,856", "212,467", "275.03"],
]

# No header here — this is the point. Real continuation pages have none.
PAGE2_ROWS = [
    ["SUB-DISTRICT", "Kupwara", "Urban", "7,008", "75,591", "44,981", "30,610", "26.91"],  # trailing part of Kupwara district
    ["DISTRICT", "Badgam", "Total", "103,363", "753,745", "398,041", "355,704", "1361.00"],
    ["SUB-DISTRICT", "Khag", "Total", "8,799", "67,596", "34,457", "33,139", "61.12"],
    ["STATE", "PUNJAB", "Total", "5,032,199", "27,743,338", "14,634,819", "13,108,519", "50362.00"],
    ["DISTRICT", "Amritsar", "Total", "441,586", "2,490,656", "1,310,075", "1,180,581", "2683.00"],
]


def build():
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4)

    def make_table(rows):
        t = Table(rows)
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        return t

    elements = [
        make_table([HEADER] + PAGE1_ROWS),
        PageBreak(),
        make_table(PAGE2_ROWS),  # deliberately no header row
    ]
    doc.build(elements)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    build()
