from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient, models

def ensure_collection(
    client: QdrantClient, 
    collection_name: str, 
    vector_size: int
) -> None:
    """
    Ensure a Qdrant collection exists, create if not.

    Args:
        client: QdrantClient instance.
        collection_name: Name of the collection.
        vector_size: Size of the embedding vectors.
    """
    try:
        client.get_collection(collection_name=collection_name)
    except Exception:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE)
        )

def upsert_vectors(
    client: QdrantClient,
    collection_name: str,
    vectors: List[List[float]],
    payloads: List[Dict[str, Any]],
    ids: Optional[List[str]] = None
) -> None:
    """
    Upsert vectors and payloads into Qdrant.

    Args:
        client: QdrantClient instance.
        collection_name: Name of the collection.
        vectors: List of embedding vectors.
        payloads: List of metadata dicts for each vector.
        ids: Optional list of string IDs for each vector.
    """
    from uuid import uuid4
    points = [
        models.PointStruct(
            id=ids[i] if ids else str(uuid4()),
            vector=vectors[i],
            payload=payloads[i]
        )
        for i in range(len(vectors))
    ]
    client.upsert(collection_name=collection_name, points=points)

def search_vectors(
    client: QdrantClient,
    collection_name: str,
    query_vector: List[float],
    limit: int = 3
) -> List[Any]:
    """
    Search for similar vectors in Qdrant.

    Args:
        client: QdrantClient instance.
        collection_name: Name of the collection.
        query_vector: Embedding vector to search with.
        limit: Number of results to return.

    Returns:
        List of Qdrant search results.
    """
    return client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=limit,
        with_payload=True
    )