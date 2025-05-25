from fastapi import FastAPI, File, UploadFile, HTTPException, Body # Body is not used for QueryRequest, ensure BaseModel is
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import time
import logging
from dotenv import load_dotenv
from pydantic import BaseModel # Make sure this is imported

import fitz  # PyMuPDF
from qdrant_client import QdrantClient
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain.docstore.document import Document as LangchainDocument
import google.generativeai as genai # Ensure this is imported
from transformers import AutoTokenizer

from hf_embeddings import get_hf_embeddings
from gemini_utils import get_gemini_model, gemini_generate_content
from qdrant_utils import ensure_collection, upsert_vectors, search_vectors

# --- Configuration & Initialization ---
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

if not all([QDRANT_URL, GEMINI_API_KEY, HF_TOKEN]):
    logger.error("Missing one or more critical environment variables: QDRANT_URL, GEMINI_API_KEY, HF_TOKEN")
    # Consider raising an exception or exiting if critical services can't initialize
else:
    logger.info("All critical environment variables seem to be present.")


# FastAPI App
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
UPLOAD_DIR = "uploads_temp" # For temporary PDF storage
os.makedirs(UPLOAD_DIR, exist_ok=True)

JINA_EMBEDDING_MODEL = "jinaai/jina-embeddings-v2-base-en"
JINA_EMBEDDING_DIMENSION = 768 # For jina-embeddings-v2-base-en

# Clients
qdrant_client = None
embeddings_model = None
gemini_model = None
tokenizer = None

try:
    if QDRANT_URL:
        qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=20)
        logger.info("Qdrant client initialized successfully.")
    else:
        logger.error("QDRANT_URL not set. Qdrant client not initialized.")
except Exception as e:
    logger.error(f"Failed to initialize Qdrant client: {e}")

try:
    if HF_TOKEN:
        embeddings_model = HuggingFaceInferenceAPIEmbeddings(
            api_key=HF_TOKEN, model_name=JINA_EMBEDDING_MODEL
        )
        logger.info("Jina embeddings model initialized successfully.")
    else:
        logger.error("HF_TOKEN not set. Embeddings model not initialized.")
except Exception as e:
    logger.error(f"Failed to initialize Jina embeddings model: {e}")

try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest') # Or 'gemini-pro'
        logger.info("Gemini client initialized successfully.")
    else:
        logger.error("GEMINI_API_KEY not set. Gemini client not initialized.")
except Exception as e:
    logger.error(f"Failed to initialize Gemini client: {e}")
    
try:
    # Tokenizer does not strictly need HF_TOKEN for public models, but good practice if private
    tokenizer = AutoTokenizer.from_pretrained(JINA_EMBEDDING_MODEL, token=HF_TOKEN if HF_TOKEN else None)
    logger.info(f"Tokenizer for {JINA_EMBEDDING_MODEL} loaded.")
except Exception as e:
    logger.error(f"Failed to load tokenizer for {JINA_EMBEDDING_MODEL}: {e}")
    # tokenizer remains None, count_tokens will fallback

def count_tokens(text: str) -> int:
    if not tokenizer:
        logger.warning("Tokenizer not available, falling back to character count for chunking.")
        return len(text)
    return len(tokenizer.encode(text))

# --- Helper Functions ---
def get_qdrant_collection_name(file_id: str) -> str:
    return f"file_collection_{file_id}"

# --- API Endpoints ---
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not qdrant_client or not embeddings_model or not tokenizer: # Removed gemini_model check as it's not used in upload
        missing_services = []
        if not qdrant_client: missing_services.append("Qdrant client")
        if not embeddings_model: missing_services.append("Embeddings model (check HF_TOKEN)")
        if not tokenizer: missing_services.append("Tokenizer")
        logger.error(f"Upload prerequisites not met: {', '.join(missing_services)}")
        raise HTTPException(status_code=503, detail=f"A backend service is not available: {', '.join(missing_services)}. Check server logs and .env configuration.")

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 100MB limit.")

    file_id = str(uuid.uuid4())
    temp_pdf_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")

    try:
        with open(temp_pdf_path, "wb") as f:
            f.write(contents)
        logger.info(f"Temporary PDF saved to {temp_pdf_path}")

        doc = fitz.open(temp_pdf_path)
        langchain_docs = []
        for page_num, page in enumerate(doc):
            page_text = page.get_text("text")
            if page_text.strip():
                langchain_docs.append(
                    LangchainDocument(
                        page_content=page_text,
                        metadata={"page_number": page_num + 1, "source_filename": file.filename}
                    )
                )
        doc.close()
        logger.info(f"Extracted {len(langchain_docs)} pages with text from {file.filename}")

        if not langchain_docs:
            raise HTTPException(status_code=400, detail="No text could be extracted from the PDF.")

        # Chunk documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,  # Target token count
            chunk_overlap=50, # Target token overlap
            length_function=count_tokens,
            add_start_index=True, # Useful for context
        )
        chunks = text_splitter.split_documents(langchain_docs)
        logger.info(f"Split content into {len(chunks)} chunks.")

        if not chunks:
            # This case should ideally be handled by the splitter or previous checks,
            # but as a safeguard:
            raise HTTPException(status_code=500, detail="Failed to split document into chunks, or document yielded no splittable content.")

        chunk_texts = [chunk.page_content for chunk in chunks]
        
        # Generate embeddings for chunks
        chunk_embeddings = get_hf_embeddings(chunk_texts, HF_TOKEN)

        collection_name = get_qdrant_collection_name(file_id)
        
        # Ensure Qdrant collection exists
        ensure_collection(qdrant_client, collection_name, JINA_EMBEDDING_DIMENSION)

        # Prepare payloads
        payloads = [
            {
                "text": chunk.page_content,
                "page_number": chunk.metadata.get("page_number"),
                "source_filename": chunk.metadata.get("source_filename"),
                "start_index": chunk.metadata.get("start_index"),
            }
            for chunk in chunks
        ]

        # Upsert vectors and payloads
        upsert_vectors(qdrant_client, collection_name, chunk_embeddings, payloads)

        return {
            "message": "File processed successfully.",
            "file_id": file_id,
            "original_filename": file.filename,
            "num_pages_extracted": len(langchain_docs),
            "num_chunks_created": len(chunks)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during PDF processing for {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error during file processing: {str(e)}")
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
            logger.info(f"Removed temporary PDF: {temp_pdf_path}")


class QueryRequest(BaseModel): # Ensure this uses BaseModel
    query: str
    rag_type: str 
    file_id: str

@app.post("/query")
async def handle_query(request: QueryRequest):
    if not qdrant_client or not embeddings_model or not gemini_model:
        missing_services = []
        if not qdrant_client: missing_services.append("Qdrant client")
        if not embeddings_model: missing_services.append("Embeddings model (check HF_TOKEN)")
        if not gemini_model: missing_services.append("Gemini client (check GEMINI_API_KEY)")
        logger.error(f"Query prerequisites not met: {', '.join(missing_services)}")
        raise HTTPException(status_code=503, detail=f"A backend service is not available for querying: {', '.join(missing_services)}. Check server logs and .env configuration.")

    start_time = time.time()
    
    query_text = request.query
    rag_type = request.rag_type
    file_id = request.file_id
    collection_name = get_qdrant_collection_name(file_id)

    logger.info(f"Received query: '{query_text}', RAG Type: {rag_type}, File ID: {file_id}")

    try:
        # 1. Embed the query
        query_embedding = get_hf_embeddings([query_text], HF_TOKEN)[0]

        retrieved_chunks_for_context = []
        search_query_for_qdrant = query_text # Original query for context display

        # 2. RAG Strategy
        if rag_type == "simple":
            search_results = search_vectors(qdrant_client, collection_name, query_embedding, limit=3)
            retrieved_chunks_for_context = search_results
            logger.info(f"Simple RAG: Retrieved {len(search_results)} chunks.")

        elif rag_type == "self_query":
            # Use Gemini to rewrite the query
            try:
                rewrite_prompt = f"Rewrite the following user query to be more effective for retrieving relevant text chunks from a document. Focus on clarity and keywords. User query: \"{query_text}\""
                rewritten_query = await gemini_generate_content(gemini_model, rewrite_prompt)
                search_query_for_qdrant = rewritten_query
                query_embedding = get_hf_embeddings([rewritten_query], HF_TOKEN)[0]
                search_results = search_vectors(qdrant_client, collection_name, query_embedding, limit=3)
                retrieved_chunks_for_context = search_results
                logger.info(f"Self-Query RAG: Retrieved {len(search_results)} chunks using query '{search_query_for_qdrant}'.")

            except Exception as e:
                logger.error(f"Self-Query: Failed to rewrite query with Gemini: {e}. Falling back to original query.")
            
            search_results = qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=3,
                with_payload=True
            )
            retrieved_chunks_for_context = search_results
            logger.info(f"Self-Query RAG: Retrieved {len(search_results)} chunks using query '{search_query_for_qdrant}'.")

        elif rag_type == "reranker":
            # Retrieve top-10 initially
            initial_search_results = search_vectors(qdrant_client, collection_name, query_embedding, limit=10)
            logger.info(f"Reranker RAG: Retrieved {len(initial_search_results)} initial chunks.")

            if initial_search_results:
                # Use Gemini to rerank (select top 3)
                rerank_prompt_parts = [f"Given the user query: \"{query_text}\"\n\nAnd the following text chunks retrieved from a document:\n"]
                for i, hit in enumerate(initial_search_results):
                    rerank_prompt_parts.append(f"Chunk {i+1} (ID: {hit.id}):\n{hit.payload['text']}\n---")
                
                rerank_prompt_parts.append("\nBased on relevance to the user query, identify the IDs of the top 3 most relevant chunks from the list above. ")
                rerank_prompt_parts.append("Return ONLY a comma-separated list of the top 3 chunk IDs (e.g., 'chunk_id_A,chunk_id_B,chunk_id_C'). Do not add any other text or explanation.")
                
                rerank_prompt_text = "".join(rerank_prompt_parts)

                try:
                    gemini_response_rerank = await gemini_model.generate_content_async(rerank_prompt_text)
                    top_ids_str = gemini_response_rerank.text.strip()
                    top_ids = [id_str.strip() for id_str in top_ids_str.split(',') if id_str.strip()] # Ensure no empty strings
                    
                    reranked_map = {str(hit.id): hit for hit in initial_search_results} # Ensure IDs are strings for lookup
                    final_reranked_chunks = [reranked_map[id_val] for id_val in top_ids if id_val in reranked_map][:3] 
                    retrieved_chunks_for_context = final_reranked_chunks
                    logger.info(f"Reranker RAG: Gemini reranked. Top IDs: {top_ids}. Selected {len(retrieved_chunks_for_context)} chunks.")

                except Exception as e:
                    logger.error(f"Reranker RAG: Failed to rerank with Gemini: {e}. Falling back to top 3 initial results.", exc_info=True)
                    retrieved_chunks_for_context = initial_search_results[:3] 
            else:
                retrieved_chunks_for_context = []
                logger.info("Reranker RAG: No initial chunks found to rerank.")
        else:
            raise HTTPException(status_code=400, detail="Invalid RAG type specified.")

        # 3. Construct context for Gemini
        context_for_gemini = "\n\n---\n\n".join([
            f"Source: {hit.payload.get('source_filename', 'N/A')}, Page: {hit.payload.get('page_number', 'N/A')}\nContent:\n{hit.payload['text']}" 
            for hit in retrieved_chunks_for_context
        ])
        
        if not retrieved_chunks_for_context:
            final_answer_text = "I could not find relevant information in the document to answer your question."
            logger.info("No relevant chunks found for Gemini prompt.")
        else:
            # 4. Call Gemini for final answer
            final_prompt = (
                f"You are a helpful AI assistant. Answer the user's question based SOLELY on the provided context from a document. "
                f"If the context does not contain the answer, say so. Do not use any external knowledge.\n\n"
                f"User Query: \"{search_query_for_qdrant}\"\n\n" # Use the (potentially rewritten) query
                f"Context from document:\n{context_for_gemini}\n\n"
                f"Answer:"
            )
            
            final_answer_text = await gemini_generate_content(gemini_model, final_prompt)

        end_time = time.time()
        
        # Prepare context chunks for frontend (include score and payload)
        formatted_context_chunks = []
        for hit in retrieved_chunks_for_context:
            formatted_context_chunks.append({
                "id": str(hit.id),
                "score": hit.score if hasattr(hit, 'score') and hit.score is not None else None,
                "text": hit.payload.get("text"),
                "page_number": hit.payload.get("page_number"),
                "source_filename": hit.payload.get("source_filename"),
                "start_index": hit.payload.get("start_index")
            })

        return {
            "answer": final_answer_text,
            "retrieved_context": formatted_context_chunks,
            "response_time_seconds": round(end_time - start_time, 2),
            "rag_type_used": rag_type,
            "query_used_for_retrieval": search_query_for_qdrant
        }

    except HTTPException: 
        raise
    except Exception as e:
        logger.error(f"Error during query processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error during query processing: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server for local development...")
    uvicorn.run(app, host="0.0.0.0", port=8000)