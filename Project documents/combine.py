import os

parts = ['build_v5.py', 'build_v5_part2.py', 'build_v5_part3.py']
with open('generate_review_doc_v5.py', 'w', encoding='utf-8') as outfile:
    for part in parts:
        with open(part, 'r', encoding='utf-8') as infile:
            content = infile.read()
            # Remove existing doc.save commands to avoid saving prematurely
            content = '\n'.join([line for line in content.split('\n') if 'doc.save' not in line])
            outfile.write(content + '\n')
            
    outfile.write('\n')
    outfile.write('doc.save(r"E:\\sam\\Project documents\\Samvak_ProjectReview_Final.docx")\n')
    outfile.write('print("Successfully generated final Word document!")\n')

print("Combined scripts into generate_review_doc_v5.py")
