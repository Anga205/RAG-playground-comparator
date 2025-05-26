# RAG Playground Comparator Backend API

This document outlines the API endpoints available in the RAG Playground Comparator backend.

## Base URL

All API routes are relative to the base URL where the FastAPI application is running.
By default, during development, this is `http://localhost:8000`.

## Endpoints

### 1. Upload PDF Chunk

*   **Endpoint:** `/upload_chunk`
*   **Method:** `POST`
*   **Description:** Uploads a chunk of a PDF file. The backend assembles these chunks into a complete PDF file named `{md5sum}.pdf` in the `uploads_pdf` directory. Once the final chunk is received, it triggers a background process to load, parse, and store the PDF content and its embeddings in a Qdrant vector database.
*   **Request Type:** `multipart/form-data`
*   **Form Data:**
    *   `file_chunk` (file): The binary data of the file chunk.
    *   `filename` (str): The target filename for the assembled PDF (expected to be in the format `{md5sum}.pdf`).
    *   `chunk_number` (int): The 0-indexed number of the current chunk.
    *   `total_chunks` (int): The total number of chunks for this file.
*   **Success Response (Intermediate Chunk):**
    *   **Status Code:** `200 OK`
    *   **Body:**
        ```json
        {
          "message": "Chunk {chunk_number + 1}/{total_chunks} for {safe_basename} received successfully"
        }
        ```
*   **Success Response (Final Chunk):**
    *   **Status Code:** `200 OK`
    *   **Body:**
        ```json
        {
          "message": "File {safe_basename} uploaded successfully",
          "filename": "{safe_basename}", // e.g., "md5sum.pdf"
          "size": 123456, // Size of the assembled file in bytes
          "md5sum": "{md5sum}" // The MD5 sum of the file
        }
        ```
*   **Error Responses:**
    *   `400 Bad Request`: If the filename format is invalid.
        ```json
        { "detail": "Invalid filename format or characters." }
        ```
    *   `500 Internal Server Error`: If there's an issue writing the chunk to disk or another unexpected error.
        ```json
        { "detail": "Could not write chunk to file: {error_message}" }
        ```
        ```json
        { "detail": "An unexpected error occurred: {error_message}" }
        ```

### 2. Simple RAG Query

*   **Endpoint:** `/simple-rag`
*   **Method:** `POST`
*   **Description:** Processes a user query using a vanilla RAG (Retrieval Augmented Generation) pipeline. It retrieves relevant chunks from the vector database and uses them as context for a language model to generate an answer.
*   **Request Type:** `application/json`
*   **Request Body:**
    ```json
    {
      "query": "Your question here"
    }
    ```
*   **Success Response:**
    *   **Status Code:** `200 OK`
    *   **Body (Example from `pipelines.vanilla_rag_pipeline`):**
        ```json
        {
          "answer": "The generated answer from the LLM.",
          "chunks": ["Relevant chunk 1 text...", "Relevant chunk 2 text..."]
        }
        ```
*   **Error Response:**
    *   `400 Bad Request`: If the `query` field is missing.
        ```json
        { "detail": "Missing 'query' in request body." }
        ```
    *   The endpoint will wait if a PDF is currently being processed (`processingPDF` is true) before handling the query.

### 3. Reranker RAG Query

*   **Endpoint:** `/reranker`
*   **Method:** `POST`
*   **Description:** Processes a user query using a RAG pipeline that includes a reranking step. It retrieves an initial set of chunks, reranks them for relevance, and then uses the top reranked chunks as context for a language model.
*   **Request Type:** `application/json`
*   **Request Body:**
    ```json
    {
      "query": "Your question here"
    }
    ```
*   **Success Response:**
    *   **Status Code:** `200 OK`
    *   **Body (Example from `pipelines.reranker_pipeline`):**
        ```json
        {
          "answer": "The generated answer from the LLM.",
          "chunks": ["Initial relevant chunk 1...", "Initial relevant chunk 2...", /* ...up to 10 */],
          "ranked_chunks": ["Reranked chunk 1...", "Reranked chunk 2..."]
        }
        ```
*   **Error Response:**
    *   `400 Bad Request`: If the `query` field is missing.
        ```json
        { "detail": "Missing 'query' in request body." }
        ```
    *   The endpoint will wait if a PDF is currently being processed (`processingPDF` is true) before handling the query.

### 4. Self-Querying RAG Query

*   **Endpoint:** `/self-query`
*   **Method:** `POST`
*   **Description:** Processes a user query using a self-querying RAG pipeline. This typically involves transforming the initial query (e.g., to extract metadata or rephrase for better retrieval) before searching the vector database and generating an answer.
*   **Request Type:** `application/json`
*   **Request Body:**
    ```json
    {
      "query": "Your question here"
    }
    ```
*   **Success Response:**
    *   **Status Code:** `200 OK`
    *   **Body (Example from `pipelines.self_querying_pipeline`):**
        ```json
        {
          "answer": "The generated answer from the LLM.",
          "refined_query": "The query embedding or refined query text used for searching.",
          "chunks": ["Relevant chunk 1 text...", "Relevant chunk 2 text..."]
        }
        ```
        *Note: If no relevant information is found, the `self_querying_pipeline` might return a string like "No relevant information found." which would then be the direct response body.*
*   **Error Response:**
    *   `400 Bad Request`: If the `query` field is missing.
        ```json
        { "detail": "Missing 'query' in request body." }
        ```
    *   The endpoint will wait if a PDF is currently being processed (`processingPDF` is true) before handling the query.

### 5. Root / Health Check

*   **Endpoint:** `/`
*   **Method:** `GET`
*   **Description:** A simple health check endpoint.
*   **Request Body:** None
*   **Success Response:**
    *   **Status Code:** `200 OK`
    *   **Body:**
        ```json
        {
          "message": "Welcome to the RAG Playground Comparator Backend!"
        }
        ```

## Notes

*   **PDF Processing:** The `load_pdf` function (triggered after a successful file upload) handles the extraction of text from PDFs, chunking the text, generating embeddings, and storing them in a Qdrant collection. This process runs in a separate thread to avoid blocking the API.
*   **Qdrant Reset:** The Qdrant collection is reset (`db_utils.reset_qdrant_collection()`) every time the FastAPI application starts. This means previously uploaded and processed PDFs will need to be re-uploaded.
*   **Concurrency Control:** A simple `processingPDF` flag with a `threading.Event().wait(1)` is used to prevent RAG queries from executing while a PDF is being ingested into the vector store.
*   **CORS:** The application is configured with `CORSMiddleware` to allow requests from all origins (`"*"`). For production, it's recommended to restrict this to specific frontend domains.

```# RAG Playground Comparator Backend API

This document outlines the API endpoints available in the RAG Playground Comparator backend.

## Base URL

All API routes are relative to the base URL where the FastAPI application is running.
By default, during development, this is `http://localhost:8000`.

## Endpoints

### 1. Upload PDF Chunk

*   **Endpoint:** `/upload_chunk`
*   **Method:** `POST`
*   **Description:** Uploads a chunk of a PDF file. The backend assembles these chunks into a complete PDF file named `{md5sum}.pdf` in the `uploads_pdf` directory. Once the final chunk is received, it triggers a background process to load, parse, and store the PDF content and its embeddings in a Qdrant vector database.
*   **Request Type:** `multipart/form-data`
*   **Form Data:**
    *   `file_chunk` (file): The binary data of the file chunk.
    *   `filename` (str): The target filename for the assembled PDF (expected to be in the format `{md5sum}.pdf`).
    *   `chunk_number` (int): The 0-indexed number of the current chunk.
    *   `total_chunks` (int): The total number of chunks for this file.
*   **Success Response (Intermediate Chunk):**
    *   **Status Code:** `200 OK`
    *   **Body:**
        ```json
        {
          "message": "Chunk {chunk_number + 1}/{total_chunks} for {safe_basename} received successfully"
        }
        ```
*   **Success Response (Final Chunk):**
    *   **Status Code:** `200 OK`
    *   **Body:**
        ```json
        {
          "message": "File {safe_basename} uploaded successfully",
          "filename": "{safe_basename}", // e.g., "md5sum.pdf"
          "size": 123456, // Size of the assembled file in bytes
          "md5sum": "{md5sum}" // The MD5 sum of the file
        }
        ```
*   **Error Responses:**
    *   `400 Bad Request`: If the filename format is invalid.
        ```json
        { "detail": "Invalid filename format or characters." }
        ```
    *   `500 Internal Server Error`: If there's an issue writing the chunk to disk or another unexpected error.
        ```json
        { "detail": "Could not write chunk to file: {error_message}" }
        ```
        ```json
        { "detail": "An unexpected error occurred: {error_message}" }
        ```

### 2. Simple RAG Query

*   **Endpoint:** `/simple-rag`
*   **Method:** `POST`
*   **Description:** Processes a user query using a vanilla RAG (Retrieval Augmented Generation) pipeline. It retrieves relevant chunks from the vector database and uses them as context for a language model to generate an answer.
*   **Request Type:** `application/json`
*   **Request Body:**
    ```json
    {
      "query": "Your question here"
    }
    ```
*   **Success Response:**
    *   **Status Code:** `200 OK`
    *   **Body (Example from `pipelines.vanilla_rag_pipeline`):**
        ```json
        {
          "answer": "The generated answer from the LLM.",
          "chunks": ["Relevant chunk 1 text...", "Relevant chunk 2 text..."]
        }
        ```
*   **Error Response:**
    *   `400 Bad Request`: If the `query` field is missing.
        ```json
        { "detail": "Missing 'query' in request body." }
        ```
    *   The endpoint will wait if a PDF is currently being processed (`processingPDF` is true) before handling the query.

### 3. Reranker RAG Query

*   **Endpoint:** `/reranker`
*   **Method:** `POST`
*   **Description:** Processes a user query using a RAG pipeline that includes a reranking step. It retrieves an initial set of chunks, reranks them for relevance, and then uses the top reranked chunks as context for a language model.
*   **Request Type:** `application/json`
*   **Request Body:**
    ```json
    {
      "query": "Your question here"
    }
    ```
*   **Success Response:**
    *   **Status Code:** `200 OK`
    *   **Body (Example from `pipelines.reranker_pipeline`):**
        ```json
        {
          "answer": "The generated answer from the LLM.",
          "chunks": ["Initial relevant chunk 1...", "Initial relevant chunk 2...", /* ...up to 10 */],
          "ranked_chunks": ["Reranked chunk 1...", "Reranked chunk 2..."]
        }
        ```
*   **Error Response:**
    *   `400 Bad Request`: If the `query` field is missing.
        ```json
        { "detail": "Missing 'query' in request body." }
        ```
    *   The endpoint will wait if a PDF is currently being processed (`processingPDF` is true) before handling the query.

### 4. Self-Querying RAG Query

*   **Endpoint:** `/self-query`
*   **Method:** `POST`
*   **Description:** Processes a user query using a self-querying RAG pipeline. This typically involves transforming the initial query (e.g., to extract metadata or rephrase for better retrieval) before searching the vector database and generating an answer.
*   **Request Type:** `application/json`
*   **Request Body:**
    ```json
    {
      "query": "Your question here"
    }
    ```
*   **Success Response:**
    *   **Status Code:** `200 OK`
    *   **Body (Example from `pipelines.self_querying_pipeline`):**
        ```json
        {
          "answer": "The generated answer from the LLM.",
          "refined_query": "The query embedding or refined query text used for searching.",
          "chunks": ["Relevant chunk 1 text...", "Relevant chunk 2 text..."]
        }
        ```
        *Note: If no relevant information is found, the `self_querying_pipeline` might return a string like "No relevant information found." which would then be the direct response body.*
*   **Error Response:**
    *   `400 Bad Request`: If the `query` field is missing.
        ```json
        { "detail": "Missing 'query' in request body." }
        ```
    *   The endpoint will wait if a PDF is currently being processed (`processingPDF` is true) before handling the query.

### 5. Root / Health Check

*   **Endpoint:** `/`
*   **Method:** `GET`
*   **Description:** A simple health check endpoint.
*   **Request Body:** None
*   **Success Response:**
    *   **Status Code:** `200 OK`
    *   **Body:**
        ```json
        {
          "message": "Welcome to the RAG Playground Comparator Backend!"
        }
        ```

## Notes

*   **PDF Processing:** The `load_pdf` function (triggered after a successful file upload) handles the extraction of text from PDFs, chunking the text, generating embeddings, and storing them in a Qdrant collection. This process runs in a separate thread to avoid blocking the API.
*   **Qdrant Reset:** The Qdrant collection is reset (`db_utils.reset_qdrant_collection()`) every time the FastAPI application starts. This means previously uploaded and processed PDFs will need to be re-uploaded.
*   **Concurrency Control:** A simple `processingPDF` flag with a `threading.Event().wait(1)` is used to prevent RAG queries from executing while a PDF is being ingested into the vector store.
*   **CORS:** The application is configured with `CORSMiddleware` to allow requests from all origins (`"*"`). For production, it's recommended to restrict this to specific frontend domains.
