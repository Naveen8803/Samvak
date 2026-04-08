import zipfile
import re

source = r'E:\sam\Project documents\Samvak_FrontPages.docx'

with zipfile.ZipFile(source, 'r') as zin:
    content = zin.read('word/document.xml').decode('utf-8')
    
    # Simple regex to get all text inside <w:t> tags
    texts = re.findall(r'<w:t(?: xml:space="preserve")?>(.*?)</w:t>', content)
    print("Found exact matches for Shaik Salim:", 'Shaik Salim' in content)
    print("Found exact matches for Naveen:", 'Uppalapati Naveen' in content)
    
    # Let's print out all texts to see how fragmented they are
    for t in texts[:100]:
        print(f"[{t}]")
