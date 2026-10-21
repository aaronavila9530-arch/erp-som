import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.request import urlopen
from pypdf import PdfReader, PdfWriter
import pypdfium2 as pdfium

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(r'C:\Users\aaron\Downloads\2246-1310-2026_FINAL.pdf')
QA=ROOT/'tmp/pdfs/draft-2246'
OUT=ROOT/'output/pdf/2246-1310-2026_FINAL_CORREGIDO.pdf'
QA.mkdir(parents=True,exist_ok=True)
URL='https://api-som-fastapi-production-e66d.up.railway.app'

def fetch(url,timeout=30):
    with urlopen(url,timeout=timeout) as response:
        return response.read()

def render(path,prefix):
    doc=pdfium.PdfDocument(str(path))
    for i in range(len(doc)):
        page=doc[i]
        image=page.render(scale=1.35).to_pil()
        image.save(QA/f'{prefix}-{i+1}.png')
        page.close()
    doc.close()

if len(sys.argv)>1 and sys.argv[1]=='before':
    render(SOURCE,'before')
    raise SystemExit()

data_url=URL+'/draft-survey/unified/2246-1310-2026/word'
before=json.loads(fetch(data_url))['data']
assert before['word_final_draft_date']=='2026-10-19'
assert before['word_initial_draft_time']=='20:00:00'
parts=[]
for route,name in [('presentation','cover'),('generate','word')]:
    content=fetch(URL+f'/draft-survey-word/{route}/2246-1310-2026',timeout=180)
    assert content.startswith(b'%PDF-')
    path=QA/(name+'.pdf');path.write_bytes(content)
    parts.append(path)
cover,word=[PdfReader(p) for p in parts]
cover_text='\n'.join(p.extract_text() for p in cover.pages)
word_text='\n'.join(p.extract_text() for p in word.pages)
assert 'October 19, 2026' in cover_text,cover_text
assert '22:35' not in cover_text and '11:40' not in cover_text,cover_text
assert 'October 19, 2026' in word_text and 'January 14, 2026' not in word_text
assert '-2.60' not in word_text and '-0.0051' not in word_text
assert 'Oct 13 2026 20:00' in word_text and 'Oct 19 2026 11:40' in word_text
for i,p in enumerate(word.pages):
    matches=re.findall(r'Page\s+(\d+)\s+of\s+(\d+)',p.extract_text())
    assert matches==[(str(i+1),str(len(word.pages)))],(i,matches)
original=PdfReader(SOURCE)
assert len(original.pages)==8
assert 'TOTAL DISCHARGED BY DRAFT SURVEY' in original.pages[3].extract_text()
assert all(len(p.extract_text().strip())<10 for p in original.pages[4:])
writer=PdfWriter()
for document in (cover,word):
    for page in document.pages:writer.add_page(page)
for page in original.pages[4:]:writer.add_page(page)
OUT.parent.mkdir(parents=True,exist_ok=True)
with OUT.open('wb') as stream:writer.write(stream)
corrected=PdfReader(OUT)
assert len(corrected.pages)==len(cover.pages)+len(word.pages)+4
def images(page):return [hashlib.sha256(image.data).hexdigest() for image in page.images]
for old,new in zip(original.pages[4:],corrected.pages[-4:]):
    assert images(old)==images(new) and images(old)
assert json.loads(fetch(data_url))['data']==before,'Business report changed during generation'
render(OUT,'after')
print(json.dumps({'pages':len(corrected.pages),'cover':len(cover.pages),'word':len(word.pages),
                  'annexes_preserved':4,'business_data_unchanged':True,'output':str(OUT)}))
