"""Extract first 30 paragraphs format from reference doc."""
from docx import Document

doc = Document(r'E:\sam\Project documents\ProjectDoc.docx')

s = doc.sections[0]
print(f"Margins: top={s.top_margin.cm:.2f} bot={s.bottom_margin.cm:.2f} left={s.left_margin.cm:.2f} right={s.right_margin.cm:.2f}")

from lxml import etree
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
borders = s._sectPr.findall('.//w:pgBorders', ns)
for b in borders:
    print(f"BORDER XML: {etree.tostring(b, pretty_print=True).decode()}")

style = doc.styles['Normal']
pf = style.paragraph_format
print(f"Normal font: {style.font.name}, size: {style.font.size}, line_spacing: {pf.line_spacing}, rule: {pf.line_spacing_rule}")

for i, p in enumerate(doc.paragraphs[:30]):
    text = p.text.strip()[:60]
    fmt = p.paragraph_format
    if not text:
        print(f"P{i}: [EMPTY]")
        continue
    sizes = set()
    bolds = set()
    for r in p.runs:
        if r.font.size: sizes.add(r.font.size)
        bolds.add(r.bold)
    print(f"P{i}: align={p.alignment} ls={fmt.line_spacing} sizes={sizes} bold={bolds}")
    print(f"     '{text}'")
