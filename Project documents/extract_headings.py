"""Extract chapter headings and structure from reference doc."""
from docx import Document

doc = Document(r'E:\sam\Project documents\ProjectDoc.docx')
for i, p in enumerate(doc.paragraphs):
    t = p.text.strip()
    if not t:
        continue
    # Find headings/chapter markers
    for kw in ['CHAPTER','1.','2.','3.','4.','5.','6.','7.','8.','9.','ABSTRACT','INTRODUCTION','CONCLUSION','BIBLIOGRAPHY','REFERENCES','TESTING','RESULT','IMPLEMENTATION','ACKNOWLEDGEMENT', 'TABLE OF CONTENTS', 'CONTENTS']:
        if t.upper().startswith(kw) or kw in t.upper():
            bolds = any(r.bold for r in p.runs)
            sizes = set(r.font.size for r in p.runs if r.font.size)
            print(f"P{i}: bold={bolds} sizes={sizes} align={p.alignment}")
            print(f"     '{t[:80]}'")
            break
