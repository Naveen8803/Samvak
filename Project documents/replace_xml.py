import zipfile
import re

source = r'E:\sam\Project documents\ProjectDoc.docx'
target = r'E:\sam\Project documents\Samvak_FrontPages.docx'

def replace_xml(content_str):
    xml_str = content_str
    
    # Title
    xml_str = xml_str.replace('ATTRIBUTE-BASED DATA SHARING SCHEME REVISITED IN CLOUD COMPUTING', 'MULTI-LINGUAL SIGN LANGUAGE TO SPEECH AND SPEECH TO SIGN TRANSLATOR')
    xml_str = xml_str.replace('ATTRIBUTE', 'MULTI-LINGUAL SIGN LANGUAGE')
    xml_str = xml_str.replace('BASED DATA SHARING SCHEME REVISITED IN CLOUD COMPUTING', 'TO SPEECH AND SPEECH TO SIGN TRANSLATOR')
    xml_str = xml_str.replace('ATTRIBUTE-BASED DATA SHARING SCHEME', 'MULTI-LINGUAL SIGN LANGUAGE TO SPEECH')
    xml_str = xml_str.replace('REVISITED IN CLOUD COMPUTING', 'AND SPEECH TO SIGN TRANSLATOR')
    
    # ID
    xml_str = xml_str.replace('2201600096', '2401600155')
    xml_str = re.sub(r'22016000.*?>9<.*?>6', '2401600155', xml_str)
    
    # Names
    xml_str = xml_str.replace('Shaik Salim', 'Uppalapati Naveen Varma')
    
    # Guide / Titles
    xml_str = xml_str.replace('Dr.R D Sathiya', 'Mrs. Swathi Voddi')
    xml_str = re.sub(r'Dr\.R.*?> D Sathiya', 'Mrs. Swathi Voddi', xml_str)
    # Replace Professor under Guide with Assistant Professor
    # Note: we need to replace the single occurrence under Guide, or all of them. In the reference doc, the guide has "Professor" below their name on the cover page.
    # The string was literally `[Profes] [sor]`
    xml_str = re.sub(r'Profes(.*?)>sor', r'Assistant Profes\1>sor', xml_str)
    
    # Year
    xml_str = xml_str.replace('2023- 24', '2025- 26')
    xml_str = xml_str.replace('2023 – 24', '2025 – 26')
    xml_str = re.sub(r'2023-(.*?)[ \t]*24', r'2025-\1 26', xml_str)
    xml_str = re.sub(r'2023(.*?)-(.*?)24', r'2025\1-\2 26', xml_str)
    
    return xml_str

with zipfile.ZipFile(source, 'r') as zin:
    with zipfile.ZipFile(target, 'w') as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == 'word/document.xml':
                xml_str = content.decode('utf-8')
                xml_str = replace_xml(xml_str)
                zout.writestr(item, xml_str.encode('utf-8'))
            elif item.filename.startswith('word/header') or item.filename.startswith('word/footer'):
                xml_str = content.decode('utf-8')
                xml_str = replace_xml(xml_str)
                zout.writestr(item, xml_str.encode('utf-8'))
            else:
                zout.writestr(item, content)

print(f"Created {target} with exact text replacement.")
