from text_utils import vanilla_get_chunks, get_self_query_embedding
from ai_utils import query_gemini, rerank_chunks_with_jina
from db_utils import search_similar_chunks

def vanilla_rag_pipeline(query_text: str) -> dict[str, str]:

    similar_chunks = vanilla_get_chunks(query_text)

    # Step 2: Construct prompt to send to Gemini
    context = "\n\n".join(similar_chunks)
    prompt = f"""You are a helpful assistant. Use the following context to answer the question as accurately as possible. If the question cannot be accurately answered with the given data just say you dont know.\n\nContext:\n{context}\n\nQuestion: {query_text}\n\nAnswer:"""

    answer = query_gemini(prompt)
    return {"chunks": similar_chunks, "answer": answer}

def reranker_pipeline(query_text: str) -> dict[str, str]:
    chunks = vanilla_get_chunks(query_text, top_k=10)
    ranked_chunks = rerank_chunks_with_jina(query_text, chunks)
    prompt = f"""You are a helpful assistant. Use the following context to answer the question as accurately as possible. If the question cannot be accurately answered with the given data just say you dont know.\n\nContext:\n{str(chr(10)*2).join(ranked_chunks)}\n\nQuestion: {query_text}\n\nAnswer:"""
    answer = query_gemini(prompt)
    return {"chunks": chunks, "ranked_chunks": ranked_chunks, "answer": answer}

def self_querying_pipeline(query_text: str, top_k: int = 10) -> dict[str, str]:
    query_embedding = get_self_query_embedding(query_text)
    chunks = search_similar_chunks(query_embedding, top_k=top_k)
    
    if not chunks:
        return "No relevant information found."

    context = "\n\n".join(chunks)
    prompt = f"""You are a helpful assistant. Use the following context to answer the question as accurately as possible. If the question cannot be accurately answered with the given data just say you don't know.\n\nContext:\n{context}\n\nQuestion: {query_text}\n\nAnswer:"""
    
    answer = query_gemini(prompt)
    return {"refined_query":query_embedding, "chunks": chunks, "answer": answer}



# sample_pdf_path = "sample.pdf"

# from pdf_utils import load_pdf_as_base64, extract_pdf_text_from_base64
# base64_pdf = load_pdf_as_base64(sample_pdf_path)
# text_from_pdf = extract_pdf_text_from_base64(base64_pdf)
# from text_utils import split_text_into_chunks, get_vector_embeddings
# from db_utils import store_embeddings_in_qdrant
# chunks = split_text_into_chunks(text_from_pdf)
# embeddings = get_vector_embeddings(chunks)
# store_embeddings_in_qdrant(chunks, embeddings)
# query_text = "What is deforestation?"

# print("Vanilla RAG Pipeline Result:")
# print(vanilla_rag_pipeline(query_text))
# print("\n\n\n\n\nReranker Pipeline Result:")
# print(reranker_pipeline(query_text))
# print("\n\n\n\n\nSelf-Querying Pipeline Result:")
# print(self_querying_pipeline(query_text))