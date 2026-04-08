import os

parts = ['build_v6.py', 'build_v5_part2.py', 'build_v5_part3.py']
with open('generate_review_doc_v6.py', 'w', encoding='utf-8') as outfile:
    for part in parts:
        with open(part, 'r', encoding='utf-8') as infile:
            content = infile.read()
            # Remove any stray doc.save
            content = '\n'.join([line for line in content.split('\n') if 'doc.save' not in line])
            outfile.write(content + '\n')
            
    outfile.write('\n')
    outfile.write('doc.save(r"E:\\sam\\Project documents\\Samvak_ProjectReview_Final_V5.docx")\n')
    outfile.write('print("Successfully generated final Word document V5!")\n')

print("Combined scripts into generate_review_doc_v6.py")
