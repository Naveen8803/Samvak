import os
from docx import Document

doc = Document(r'E:\sam\Project documents\ProjectDoc.docx')

def replace_in_runs(paragraphs):
    for p in paragraphs:
        for run in p.runs:
            if 'ATTRIBUTE-BASED DATA SHARING SCHEME REVISITED IN CLOUD COMPUTING' in run.text:
                run.text = run.text.replace('ATTRIBUTE-BASED DATA SHARING SCHEME REVISITED IN CLOUD COMPUTING', 'MULTI-LINGUAL SIGN LANGUAGE TO SPEECH AND SPEECH TO SIGN TRANSLATOR')
            if 'Shaik Salim' in run.text:
                run.text = run.text.replace('Shaik Salim', 'Uppalapati Naveen Varma')
            if '2201600096' in run.text:
                run.text = run.text.replace('2201600096', '2401600155')
            if 'Dr.R D Sathiya' in run.text:
                run.text = run.text.replace('Dr.R D Sathiya', 'Mrs. Swathi Voddi')
            if '2023- 24' in run.text:
                run.text = run.text.replace('2023- 24', '2025- 26')
            if '2023 – 24' in run.text:
                run.text = run.text.replace('2023 – 24', '2025 – 26')
            if 'ATTRIBUTE' in run.text:
                run.text = run.text.replace('ATTRIBUTE', 'MULTI-LINGUAL SIGN LANGUAGE')

# The text could be split across multiple runs.
# A safer way to replace text in docx without breaking runs is to build a full string, replace it, and then clear all runs and add one run. 
# But that destroys bold/italic formatting.
