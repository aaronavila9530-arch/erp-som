import os
import win32com.client


# ============================================================
# CONVERT WORD TO PDF USING MICROSOFT WORD ENGINE (WINDOWS)
# ============================================================

def convert_word_to_pdf(word_path: str) -> str:

    if not os.path.exists(word_path):
        raise RuntimeError("Word file not found")

    pdf_path = word_path.replace(".docx", ".pdf")

    word = None

    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False

        doc = word.Documents.Open(word_path)

        # 17 = wdFormatPDF
        doc.SaveAs(pdf_path, FileFormat=17)

        doc.Close(False)

    except Exception as e:
        raise RuntimeError(f"PDF conversion failed: {e}")

    finally:
        if word:
            word.Quit()

    if not os.path.exists(pdf_path):
        raise RuntimeError("PDF file was not created")

    return pdf_path
