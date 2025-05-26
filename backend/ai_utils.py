import google.generativeai as genai
import os, requests

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