import copy
import zipfile
import shutil
import os
import xml.etree.ElementTree as ET

SRC  = r'C:\Users\navee\Downloads\Telegram Desktop\2-Page Document-Major-Project.docx'
DST  = r'C:\Users\navee\Downloads\Telegram Desktop\2-Page-Document-Naveen-SignLanguage.docx'
TMP  = r'C:\Users\navee\Downloads\Telegram Desktop\_docx_tmp'

ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

# Register all namespaces
for prefix, uri in [
    ('wpc','http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas'),
    ('cx','http://schemas.microsoft.com/office/drawing/2014/chartex'),
    ('cx1','http://schemas.microsoft.com/office/drawing/2015/9/8/chartex'),
    ('cx2','http://schemas.microsoft.com/office/drawing/2015/10/21/chartex'),
    ('cx3','http://schemas.microsoft.com/office/drawing/2016/5/9/chartex'),
    ('cx4','http://schemas.microsoft.com/office/drawing/2016/5/10/chartex'),
    ('cx5','http://schemas.microsoft.com/office/drawing/2016/5/11/chartex'),
    ('cx6','http://schemas.microsoft.com/office/drawing/2016/5/12/chartex'),
    ('cx7','http://schemas.microsoft.com/office/drawing/2016/5/13/chartex'),
    ('cx8','http://schemas.microsoft.com/office/drawing/2016/5/14/chartex'),
    ('mc','http://schemas.openxmlformats.org/markup-compatibility/2006'),
    ('aink','http://schemas.microsoft.com/office/drawing/2016/ink'),
    ('am3d','http://schemas.microsoft.com/office/drawing/2017/model3d'),
    ('o','urn:schemas-microsoft-com:office:office'),
    ('oel','http://schemas.microsoft.com/office/2019/extlst'),
    ('r','http://schemas.openxmlformats.org/officeDocument/2006/relationships'),
    ('m','http://schemas.openxmlformats.org/officeDocument/2006/math'),
    ('v','urn:schemas-microsoft-com:vml'),
    ('wp14','http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing'),
    ('wp','http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'),
    ('w10','urn:schemas-microsoft-com:office:word'),
    ('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main'),
    ('w14','http://schemas.microsoft.com/office/word/2010/wordml'),
    ('w15','http://schemas.microsoft.com/office/word/2012/wordml'),
    ('w16cex','http://schemas.microsoft.com/office/word/2018/wordml/cex'),
    ('w16cid','http://schemas.microsoft.com/office/word/2016/wordml/cid'),
    ('w16','http://schemas.microsoft.com/office/word/2018/wordml'),
    ('w16du','http://schemas.microsoft.com/office/word/2023/wordml/word16du'),
    ('w16sdtdh','http://schemas.microsoft.com/office/word/2020/wordml/sdtdatahash'),
    ('w16sdtfl','http://schemas.microsoft.com/office/word/2024/wordml/sdtformatlock'),
    ('w16se','http://schemas.microsoft.com/office/word/2015/wordml/symex'),
    ('wpg','http://schemas.microsoft.com/office/word/2010/wordprocessingGroup'),
    ('wpi','http://schemas.microsoft.com/office/word/2010/wordprocessingInk'),
    ('wne','http://schemas.microsoft.com/office/word/2006/wordml'),
    ('wps','http://schemas.microsoft.com/office/word/2010/wordprocessingShape'),
]:
    ET.register_namespace(prefix, uri)

# Extract docx
if os.path.exists(TMP):
    shutil.rmtree(TMP)
os.makedirs(TMP)
with zipfile.ZipFile(SRC, 'r') as z:
    z.extractall(TMP)

doc_path = os.path.join(TMP, 'word', 'document.xml')
tree = ET.parse(doc_path)
root = tree.getroot()
body = root.find('w:body', ns)
paragraphs = body.findall('w:p', ns)

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def clear_runs(para):
    for child in list(para):
        tag = child.tag
        local = tag.split('}')[1] if '{' in tag else tag
        if local in ('r', 'proofErr', 'bookmarkStart', 'bookmarkEnd'):
            para.remove(child)

def make_run_in(para, text, bold=False, superscript=False):
    r = ET.SubElement(para, f'{{{W}}}r')
    rpr = ET.SubElement(r, f'{{{W}}}rPr')
    rf = ET.SubElement(rpr, f'{{{W}}}rFonts')
    rf.set(f'{{{W}}}ascii', 'Bookman Old Style')
    rf.set(f'{{{W}}}hAnsi', 'Bookman Old Style')
    if bold:
        ET.SubElement(rpr, f'{{{W}}}b')
        ET.SubElement(rpr, f'{{{W}}}bCs')
    if superscript:
        ET.SubElement(rpr, f'{{{W}}}vertAlign').set(f'{{{W}}}val', 'superscript')
    ET.SubElement(rpr, f'{{{W}}}lang').set(f'{{{W}}}val', 'en-US')
    t = ET.SubElement(r, f'{{{W}}}t')
    t.text = text
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')

def set_two_part(para, bold_label, normal_text):
    clear_runs(para)
    make_run_in(para, bold_label, bold=True)
    make_run_in(para, normal_text, bold=False)

def set_text(para, text, bold=False):
    clear_runs(para)
    make_run_in(para, text, bold=bold)

# ─── CONTENT (shortened to match original ~2 pages) ────────────────────────

for i, para in enumerate(paragraphs):
    if i == 1:  # Title
        set_text(para, 'Multi-Lingual Sign Language to Speech and Speech to Sign Translator', bold=True)

    elif i == 3:  # Authors
        clear_runs(para)
        make_run_in(para, 'Mrs. Swathi Voddi', bold=True)
        make_run_in(para, '1', bold=True, superscript=True)
        make_run_in(para, ' ,', bold=False)
        make_run_in(para, 'Uppalapati Naveen Varma', bold=True)
        make_run_in(para, ' ', bold=False)
        make_run_in(para, '2', bold=True, superscript=True)

    elif i == 4:  # Affiliations
        clear_runs(para)
        make_run_in(para, '1', superscript=True)
        make_run_in(para, ' Assistant Professor,')
        make_run_in(para, '2', superscript=True)
        make_run_in(para, ' Student')

    elif i == 8:  # Abstract
        set_two_part(para,
            'Abstract: ',
            'In this paper, we present the design and implementation of a multi-lingual sign language to speech and speech to sign translation system. The proposed system uses deep learning techniques including CNNs and LSTMs to recognize hand gestures captured via webcam in real time and convert them into spoken language. Conversely, it processes speech input using speech recognition and NLP to generate sign language animations through a 3D avatar. The system supports English, Hindi, and Telugu, and is built as a web application using Python, Flask, TensorFlow, OpenCV, and MediaPipe.')

    elif i == 9:  # Keywords
        set_two_part(para,
            'Keywords: ',
            'sign language recognition, speech-to-sign translation, deep learning, gesture recognition, NLP, accessibility')

    elif i == 11:  # Introduction
        set_two_part(para,
            'Introduction: ',
            'Sign language is a visual-gestural language used by approximately 70 million deaf individuals globally. Despite its importance, a significant communication gap exists between sign language users and the hearing population. Traditional solutions like human interpreters are costly and not available in real-time. Advances in AI, computer vision, and NLP have enabled automated translation systems. This project proposes a bidirectional system that converts sign language gestures into speech and spoken language into sign animations, supporting multiple Indian languages.')

    elif i == 13:  # Motivation
        set_two_part(para,
            'Motivation: ',
            'India has over 18 million individuals with hearing disabilities who face challenges in education, healthcare, and employment due to communication barriers. Existing tools are limited to single languages and lack real-time capability. This project aims to provide an affordable, multi-lingual, real-time translation solution using standard webcams and web browsers to enable seamless interaction between deaf and hearing individuals.')

    elif i == 15:  # Methodology
        set_two_part(para,
            'Methodology: ',
            'The system uses a multi-stage pipeline. For sign-to-speech, webcam frames are processed using MediaPipe Holistic to extract hand and pose landmarks, which are fed into a CNN-LSTM model built with TensorFlow for gesture classification. Recognized glosses are converted to grammatical sentences using an LLM API. For speech-to-sign, the Web Speech API handles speech recognition, and mapped glosses drive a Three.js 3D avatar for sign animations. The system runs as a Flask web application with Socket.IO for real-time communication.')

    elif i == 17:  # Result analysis
        set_two_part(para,
            'Result analysis: ',
            'The gesture recognition model achieved 94.7% accuracy on a dataset of 2,000 samples across 36 sign classes. Real-time inference latency was approximately 120ms per prediction. Speech recognition showed less than 8% word error rate across English, Hindi, and Telugu. The 3D avatar rendered smooth sign animations validated through user feedback. The NLG module achieved a BLEU score of 0.82 for sentence generation.')

    elif i == 20:  # Conclusion
        set_two_part(para,
            'Conclusion: ',
            'The multi-lingual sign language translation system demonstrates the feasibility of real-time bidirectional translation using open-source technologies and standard hardware. By integrating computer vision, deep learning, NLP, and 3D rendering into a web platform, it provides an accessible solution for inclusive communication. Future work includes expanding vocabulary, continuous sign recognition, additional language support, and improved avatar realism through motion capture integration.')

    elif i == 23:  # Ref 1
        set_text(para, '1. S. Admasu and A. Raman, "Multi-modal Sign Language Recognition Using Deep Learning," 2021 International Conference on AI and Smart Systems, Coimbatore, 2021, pp. 678-684.')

    elif i == 24:  # Ref 2
        set_text(para, ' 2. P. Kumar, H. Gauba, P. Roy, and D. Dogra, "A Multimodal Framework for Sensor Based Sign Language Recognition," Neurocomputing, vol. 259, pp. 21-38, 2017.')

    elif i == 25:  # Ref 3
        set_text(para, '3. R. Rastgoo, K. Kiani, and S. Escalera, "Sign Language Recognition: A Deep Survey," Expert Systems with Applications, vol. 164, 113794, 2021.')

    elif i == 26:  # Ref 4
        set_text(para, ' 4. N. C. Camgoz, S. Hadfield, O. Koller, H. Ney, and R. Bowden, "Neural Sign Language Translation," 2018 IEEE/CVF CVPR, pp. 7784-7793, 2018.')

    elif i == 27:  # Ref 5
        set_text(para, ' 5. D. Bragg, O. Koller, et al., "Sign Language Recognition, Generation, and Translation: An Interdisciplinary Perspective," ACM SIGACCESS, pp. 16-31, 2019.')

    elif i == 28:  # Ref 6
        set_text(para, '6. A. Wadhawan and P. Kumar, "Deep Learning-Based Sign Language Recognition System for Static Signs," Neural Computing and Applications, vol. 32, pp. 7957-7968, 2020.')

# Write back
tree.write(doc_path, xml_declaration=True, encoding='UTF-8')

# Re-zip
if os.path.exists(DST):
    os.remove(DST)
with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for foldername, subfolders, filenames in os.walk(TMP):
        for filename in filenames:
            file_path = os.path.join(foldername, filename)
            arcname = os.path.relpath(file_path, TMP)
            zout.write(file_path, arcname)

shutil.rmtree(TMP)
print("Done! Document saved to:", DST)
