import base64
import io
import warnings
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
import fitz
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import google.generativeai as genai
import requests

# Suppress specific transformers warnings about model weights
warnings.filterwarnings("ignore", message="Some weights of the model checkpoint.*were not used when initializing.*")
warnings.filterwarnings("ignore", message="Some weights of BertModel were not initialized from the model checkpoint.*")

# Load the tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("jinaai/jina-embeddings-v2-base-en")
model = AutoModel.from_pretrained("jinaai/jina-embeddings-v2-base-en")
model.eval()


def extract_pdf_text_from_base64(b64_pdf: str) -> str:
    pdf_bytes = base64.b64decode(b64_pdf)
    pdf_stream = io.BytesIO(pdf_bytes)
    output = []
    with fitz.open(stream=pdf_stream, filetype="pdf") as doc:
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            output.append(text)
    return "\n".join(output)

def load_pdf_as_base64(pdf_path: str) -> str:
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    return base64.b64encode(pdf_bytes).decode("utf-8")

def split_text_into_chunks(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_text(text)

def get_vector_embeddings(chunks):
    embeddings = []
    for text in chunks:
        # Tokenize the input text
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        
        # Forward pass through the model
        with torch.no_grad():
            outputs = model(**inputs)
        
        # Mean pooling
        last_hidden_state = outputs.last_hidden_state
        attention_mask = inputs['attention_mask']
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        sum_embeddings = torch.sum(last_hidden_state * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        embedding = sum_embeddings / sum_mask

        # Normalize the embedding
        embedding = F.normalize(embedding, p=2, dim=1)

        embeddings.append(embedding.squeeze().tolist())
    return embeddings

def store_embeddings_in_qdrant(chunks, embeddings, collection_name="pdf_chunks"):
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    if client.collection_exists(collection_name=collection_name):
        client.delete_collection(collection_name=collection_name)

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=len(embeddings[0]),
            distance=Distance.COSINE
        ),
    )
    points = [
        PointStruct(
            id=i,
            vector=embeddings[i],
            payload={"text": chunks[i]}
        )
        for i in range(len(embeddings))
    ]
    client.upsert(collection_name=collection_name, points=points)

def search_similar_chunks(query_embedding, top_k=3, collection_name="pdf_chunks"):
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    results = client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=top_k
    )
    return [res.payload["text"] for res in results]

def vanilla_get_chunks(query_text:str, top_k:int = 3) -> list[str]:
    query_inputs = tokenizer(query_text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**query_inputs)
    last_hidden_state = outputs.last_hidden_state
    attention_mask = query_inputs['attention_mask']
    mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    sum_embeddings = torch.sum(last_hidden_state * mask_expanded, 1)
    sum_mask = torch.clamp(mask_expanded.sum(1), min=1e-9)
    query_embedding = (sum_embeddings / sum_mask)
    query_embedding = F.normalize(query_embedding, p=2, dim=1).squeeze().tolist()
    similar_chunks = search_similar_chunks(query_embedding, top_k=top_k)
    return similar_chunks

def initialize_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("models/gemini-2.5-flash-preview-04-17")
    # return genai.GenerativeModel("models/gemini-2.0-flash-lite-001")

def query_gemini(prompt: str) -> str:
    model = initialize_gemini()
    response = model.generate_content(prompt)
    return response.text

def vanilla_rag_pipeline(query_text: str) -> str:

    similar_chunks = vanilla_get_chunks(query_text)

    # Step 2: Construct prompt to send to Gemini
    context = "\n\n".join(similar_chunks)
    prompt = f"""You are a helpful assistant. Use the following context to answer the question as accurately as possible. If the question cannot be accurately answered with the given data just say you dont know.\n\nContext:\n{context}\n\nQuestion: {query_text}\n\nAnswer:"""

    answer = query_gemini(prompt)
    return answer

def rerank_chunks_with_jina(query: str, chunks: list[str], top_n: int = 3) -> list[str]:
    api_key = os.getenv("JINA_API_KEY")
    if not api_key:
        raise ValueError("JINA_API_KEY not found in environment variables.")

    url = "https://api.jina.ai/v1/rerank"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "jina-reranker-v2-base-multilingual",
        "query": query,
        "documents": chunks,
        "top_n": top_n,
        "return_documents": True
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()

    # Sort results by relevance_score descending
    ranked_results = sorted(data["results"], key=lambda r: r["relevance_score"], reverse=True)

    # Extract only the text content
    ranked_texts = [res["document"]["text"] for res in ranked_results]
    return ranked_texts

def reranker_pipeline(query_text: str) -> list[str]:
    chunks = vanilla_get_chunks(query_text, top_k=10)
    ranked_chunks = rerank_chunks_with_jina(query_text, chunks)
    prompt = f"""You are a helpful assistant. Use the following context to answer the question as accurately as possible. If the question cannot be accurately answered with the given data just say you dont know.\n\nContext:\n{str(chr(10)*2).join(ranked_chunks)}\n\nQuestion: {query_text}\n\nAnswer:"""
    answer = query_gemini(prompt)
    return answer

def extract_query_insights(query_text: str, max_retries: int = 3) -> dict:
    prompt = f"""You are an intelligent assistant that transforms natural language queries into structured information to improve search results.\n\nGiven the question: "{query_text}"\n\nReturn a JSON with the following fields:\n- "keywords": important terms to use in search\n- "topics": broader themes\n- "intent": is the user asking for definition, cause, impact, solution, etc.?\n\nRespond with only the JSON object.\n"""
    for attempt in range(max_retries):
        response = query_gemini(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            if attempt == max_retries - 1:
                return {"keywords": [], "topics": [], "intent": "unknown"}
    return {"keywords": [], "topics": [], "intent": "unknown"}

def get_self_query_embedding(query_text: str) -> list[float]:
    """Use Gemini to reformulate the query and compute its embedding."""
    insights = extract_query_insights(query_text)
    enriched_query = f"{query_text}. Keywords: {', '.join(insights['keywords'])}. Intent: {insights['intent']}. Topics: {', '.join(insights['topics'])}"
    
    inputs = tokenizer(enriched_query, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)

    last_hidden_state = outputs.last_hidden_state
    attention_mask = inputs['attention_mask']
    mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    sum_embeddings = torch.sum(last_hidden_state * mask_expanded, 1)
    sum_mask = torch.clamp(mask_expanded.sum(1), min=1e-9)
    query_embedding = F.normalize(sum_embeddings / sum_mask, p=2, dim=1)
    return query_embedding.squeeze().tolist()

def self_querying_pipeline(query_text: str, top_k: int = 10) -> str:
    query_embedding = get_self_query_embedding(query_text)
    chunks = search_similar_chunks(query_embedding, top_k=top_k)
    
    if not chunks:
        return "No relevant information found."

    context = "\n\n".join(chunks)
    prompt = f"""You are a helpful assistant. Use the following context to answer the question as accurately as possible. If the question cannot be accurately answered with the given data just say you don't know.\n\nContext:\n{context}\n\nQuestion: {query_text}\n\nAnswer:"""
    
    return query_gemini(prompt)



# sample_pdf_path = "sample.pdf"
# base64_pdf = load_pdf_as_base64(sample_pdf_path)
# text_from_pdf = extract_pdf_text_from_base64(base64_pdf)
# chunks = split_text_into_chunks(text_from_pdf)
# embeddings = get_vector_embeddings(chunks)
# store_embeddings_in_qdrant(chunks, embeddings)
query_text = "What is deforestation?"

print(self_querying_pipeline(query_text))