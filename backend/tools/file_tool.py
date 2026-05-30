import os
from pypdf import PdfReader
from docx import Document
import pandas as pd

def read_file_content(file_path):

    file_type = ""
    file_content = ""

    if file_path:
        try:
            
            extension = os.path.splitext(file_path)[1].lower()
            
            if extension in [".txt", ".md", ".csv", ".json", ".py", ".js", ".cs"]:
                file_type = "text"
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()[:10000]
            
            # PDF
            elif extension == ".pdf":
                file_type = "pdf"
                reader = PdfReader(file_path)
                file_content = ""

                for page in reader.pages:
                    file_content += page.extract_text() or ""
            
            # Word (.docx)
            elif extension in [".doc", ".docx"]:
                file_type = "doc"
                doc = Document(file_path)
                file_content = "\n".join(
                    p.text for p in doc.paragraphs
                )

            # Excel (.xlsx)
            elif extension in [".xls", ".xlsx"]:
                file_type = "excel"
                df = pd.read_excel(file_path)
                file_content = df.to_string()

            elif extension in [".jpg", ".jpeg", ".png", ".webp"]:
                file_type = "image"
                file_content = file_path

            

        except Exception as e:        
            file_content = (
                    f"Uploaded file available at: {file_path}\n"
                    f"Could not read content: {str(e)}"
                )


    return {
        "type": file_type,
        "content": file_content
    }