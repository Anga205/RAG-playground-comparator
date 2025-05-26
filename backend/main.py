from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import logging

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

    # Sanitize filename to prevent path traversal, using only the basename
    safe_basename = Path(filename).name
    file_path = UPLOADS_DIR / safe_basename

    logger.info(
        f"Receiving chunk {chunk_number + 1}/{total_chunks} for {safe_basename} "
        f"(Original chunk name from browser: {file_chunk.filename})"
    )

    try:
        # Determine file mode: 'wb' (write binary) for the first chunk, 'ab' (append binary) for others.
        mode = "wb" if chunk_number == 0 else "ab"
        
        # Read the content of the uploaded chunk
        chunk_content = await file_chunk.read()

        # Write the chunk content to the file
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
        # It's good practice to close the UploadFile, though FastAPI might handle it.
        await file_chunk.close()

    if chunk_number == total_chunks - 1:
        # This is the last chunk, the file upload is complete.
        final_size = file_path.stat().st_size if file_path.exists() else 0
        logger.info(f"File {safe_basename} uploaded successfully. Total size: {final_size} bytes.")
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
async def simple_rag(query: str = Form(...)):
    """
    Placeholder for the simple RAG endpoint.
    This can be implemented later as per requirements.
    """
    print(f"Received query: {query}")
    return {"response": f"Simple RAG endpoint is under construction. Received query: {query}"}

@app.post("/reranker")
async def reranker(query: str = Form(...)):
    """
    Placeholder for the reranker endpoint.
    This can be implemented later as per requirements.
    """
    print(f"Received query for reranking: {query}")
    return {"response": f"Reranker endpoint is under construction. Received query: {query}"}

@app.post("/self-query")
async def self_query(query: str = Form(...)):
    """
    Placeholder for the self-query endpoint.
    This can be implemented later as per requirements.
    """
    print(f"Received self-query: {query}")
    return {"response": f"Self-query endpoint is under construction. Received query: {query}"}

@app.get("/")
async def root():
    return {"message": "Welcome to the RAG Playground Comparator Backend!"}