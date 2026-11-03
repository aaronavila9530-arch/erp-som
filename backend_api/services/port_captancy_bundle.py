"""Bounded, in-memory PDF annexes; never persisted to a report or filesystem."""
from io import BytesIO
from fastapi import HTTPException
from pypdf import PdfReader, PdfWriter

def read_annexes(files):
    if not files or len(files)>10:
        raise HTTPException(422, 'Seleccione entre 1 y 10 anexos PDF')
    result=[];total=0;pages=0
    try:
        for file in files:
            data=file.file.read(20*1024*1024+1);total+=len(data)
            if len(data)>20*1024*1024 or total>40*1024*1024:
                raise HTTPException(413, 'Anexos: maximo 20 MB por archivo y 40 MB en total')
            try:
                reader=PdfReader(BytesIO(data))
                if reader.is_encrypted:raise ValueError('Encrypted')
                pages+=len(reader.pages)
                if not reader.pages or pages>300:raise ValueError('Page limit')
            except Exception:
                raise HTTPException(422, 'Anexo invalido, protegido o superior al limite de 300 paginas')
            result.append(data)
        return result
    finally:
        for file in files:file.file.close()

def merge(report, annexes):
    with PdfWriter() as writer:
        for data in [report,*annexes]:
            reader=PdfReader(BytesIO(data))
            for page in reader.pages:
                writer.add_page(page, excluded_keys=['/AA'])
        output=BytesIO();writer.write(output);return output.getvalue()
