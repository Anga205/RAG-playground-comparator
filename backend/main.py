from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import fitz

app = FastAPI()

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 100MB limit.")

    # Save PDF temporarily in memory for PyMuPDF
    pdf_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(pdf_path, "wb") as f:
        f.write(contents)

    # Extract text using PyMuPDF
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        os.remove(pdf_path)
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {str(e)}")

    # Save extracted text to a .txt file
    txt_filename = os.path.splitext(file.filename)[0] + ".txt"
    txt_path = os.path.join(UPLOAD_DIR, txt_filename)
    with open(txt_path, "w", encoding="utf-8") as txt_file:
        txt_file.write(text)

    # Remove the original PDF file
    os.remove(pdf_path)

    return {"filename": file.filename, "txt_file": txt_filename, "txt_path": txt_path}