import zipfile
import xml.etree.ElementTree as ET

docx_path = r'C:\Users\navee\Downloads\Telegram Desktop\2-Page-Document-Naveen-SignLanguage.docx'
z = zipfile.ZipFile(docx_path)
tree = ET.parse(z.open('word/document.xml'))
root = tree.getroot()
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
paragraphs = root.findall('.//w:p', ns)
for i, para in enumerate(paragraphs):
    texts = []
    for run in para.findall('.//w:r', ns):
        for t in run.findall('w:t', ns):
            if t.text:
                texts.append(t.text)
    line = ''.join(texts).strip()
    if line:
        short = line[:120] + ('...' if len(line)>120 else '')
        print(f'P{i}: {short}')
    else:
        print(f'P{i}: [empty]')
