from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import pdf_utils, text_utils, db_utils, logging, threading, pipelines
from fastapi import Request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Define the directory to store uploaded PDF files
UPLOADS_DIR = Path("uploads_pdf")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True) # Create the directory if it doesn't exist

db_utils.reset_qdrant_collection() # Reset the Qdrant collection at startup
pdfs_loaded = []
processingPDF = False
def load_pdf(name):
    global processingPDF
    while processingPDF:
        logger.info("Waiting for PDF processing to finish...")
        threading.Event().wait(1)
    processingPDF = True
    if name in pdfs_loaded:
        logger.info(f"PDF {name} already loaded. Skipping.")
        return
    pdf_path = UPLOADS_DIR / name
    if pdf_path.exists():
        logger.info(f"Loading PDF: {name}")
        pdfs_loaded.append(name)
        base64_pdf = pdf_utils.load_pdf_as_base64(pdf_path)
        text_from_pdf = pdf_utils.extract_pdf_text_from_base64(base64_pdf)
        chunks = text_utils.split_text_into_chunks(text_from_pdf)
        embeddings = text_utils.get_vector_embeddings(chunks)
        db_utils.store_embeddings_in_qdrant(chunks, embeddings)
        logger.info(f"PDF {name} loaded and processed successfully.")
    else:
        logger.warning(f"PDF file {name} does not exist in uploads directory.")
    processingPDF = False

@app.post("/upload_chunk")
async def upload_chunk(
    file_chunk: UploadFile = File(...),
    filename: str = Form(...),       # Expected to be md5sum.pdf
    chunk_number: int = Form(...),
    total_chunks: int = Form(...),
):
    """
    Receives a chunk of a file and appends it to the target file.
    The target filename is expected to be {md5sum}.pdf.
    """
    # Basic security check for the filename
    if not filename.endswith(".pdf") or ".." in filename or "/" in filename:
        logger.warning(f"Attempt to upload with invalid filename pattern: {filename}")
        raise HTTPException(status_code=400, detail="Invalid filename format or characters.")

    safe_basename = Path(filename).name
    file_path = UPLOADS_DIR / safe_basename

    logger.info(
        f"Receiving chunk {chunk_number + 1}/{total_chunks} for {safe_basename} "
        f"(Original chunk name from browser: {file_chunk.filename})"
    )

    try:
        mode = "wb" if chunk_number == 0 else "ab"
        
        chunk_content = await file_chunk.read()

        with open(file_path, mode) as f:
            f.write(chunk_content)
        
        logger.info(f"Chunk {chunk_number + 1}/{total_chunks} for {safe_basename} written to disk.")

    except IOError as e:
        logger.error(f"IOError while writing chunk for {safe_basename}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not write chunk to file: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while processing chunk for {safe_basename}: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    finally:
        await file_chunk.close()

    if chunk_number == total_chunks - 1:
        # This is the last chunk, the file upload is complete.
        final_size = file_path.stat().st_size if file_path.exists() else 0
        logger.info(f"File {safe_basename} uploaded successfully. Total size: {final_size} bytes.")
        threading.Thread(target=load_pdf, args=(safe_basename,)).start()
        return {
            "message": f"File {safe_basename} uploaded successfully",
            "filename": safe_basename,
            "size": final_size,
            "md5sum": safe_basename.replace(".pdf", "") # Assuming filename is md5sum.pdf
        }
    else:
        # More chunks are expected.
        return {
            "message": f"Chunk {chunk_number + 1}/{total_chunks} for {safe_basename} received successfully"
        }

@app.post("/simple-rag")
async def simple_rag(request: Request):
    data = await request.json()
    query = data.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Missing 'query' in request body.")
    while processingPDF:
        logger.info("Waiting for PDF processing to finish...")
        threading.Event().wait(1)
    logger.info(f"Processing query: {query}")
    response = pipelines.vanilla_rag_pipeline(query)
    return response

@app.post("/reranker")
async def reranker(request: Request):
    data = await request.json()
    query = data.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Missing 'query' in request body.")
    while processingPDF:
        logger.info("Waiting for PDF processing to finish...")
        threading.Event().wait(1)
    response = pipelines.reranker_pipeline(query)
    return response

@app.post("/self-query")
async def self_query(request: Request):
    data = await request.json()
    query = data.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Missing 'query' in request body.")
    while processingPDF:
        logger.info("Waiting for PDF processing to finish...")
        threading.Event().wait(1)
    logger.info(f"Processing self-query: {query}")
    response = pipelines.self_querying_pipeline(query)
    return response

@app.get("/")
async def root():
    return {"message": "Welcome to the RAG Playground Comparator Backend!"}