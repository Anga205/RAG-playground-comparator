import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

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

def reset_qdrant_collection(collection_name="pdf_chunks"):
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    if client.collection_exists(collection_name=collection_name):
        client.delete_collection(collection_name=collection_name)
        print(f"Collection '{collection_name}' deleted.")
    else:
        print(f"Collection '{collection_name}' does not exist.")